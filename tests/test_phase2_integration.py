"""Phase 2 系统集成测试.

测试三个核心系统的协同工作.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from simple_tools.utils.errors import ErrorContext, ToolError
from simple_tools.utils.performance_optimizer import PerformanceMonitor
from simple_tools.utils.smart_interactive import (
    SmartInteractiveSession,
    smart_confirm,
    smart_confirm_sync,
)


class TestPhase2Integration:
    """Phase 2 系统集成测试"""

    def test_error_handling_with_smart_interaction(self) -> None:
        """测试错误处理与智能交互的集成"""

        # 模拟一个会产生错误的操作
        def risky_operation() -> None:
            try:
                # 模拟文件不存在错误
                raise FileNotFoundError("test.txt not found")
            except FileNotFoundError as e:
                # 使用标准的 from_exception 方法
                error = ToolError.from_exception(
                    e,
                    context=ErrorContext(
                        operation="file_processing", file_path="test.txt"
                    ),
                )

                # 智能交互：询问用户是否继续
                # 修复：直接mock异步输入方法而不是input函数
                with patch.object(
                    SmartInteractiveSession, "_get_user_input_async", return_value="n"
                ):
                    should_continue = smart_confirm_sync(
                        operation="处理错误后继续",
                        files_affected=["test.txt"],
                        estimated_impact="medium",
                    )

                if not should_continue:
                    raise error

        with pytest.raises(ToolError) as exc_info:
            risky_operation()

        assert exc_info.value.error_code == "FILE_NOT_FOUND"
        assert "检查文件路径是否正确" in exc_info.value.suggestions

    def test_performance_monitoring_with_error_handling(self) -> None:
        """测试性能监控与错误处理的集成"""
        with patch("simple_tools.utils.performance_optimizer.logfire") as mock_logfire:
            # 修复：让装饰器能够捕获异常并记录错误
            @PerformanceMonitor.monitor_performance("integration_test")
            def failing_operation() -> None:
                # 模拟一个会失败的操作
                raise ValueError("Integration test error")

            # 测试装饰器是否正确处理异常
            with pytest.raises(ValueError):
                failing_operation()

            # 验证性能监控记录了错误
            mock_logfire.error.assert_called()
            mock_logfire.span.assert_called()

            # 验证错误信息包含预期内容
            error_call = mock_logfire.error.call_args
            assert "操作失败: integration_test" in error_call[0][0]
            assert "Integration test error" in str(error_call[1]["error"])

    @pytest.mark.asyncio
    async def test_full_workflow_integration(self) -> None:
        """测试完整工作流集成"""
        # 创建临时文件用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_files = []

            # 创建测试文件
            for i in range(5):
                file_path = temp_path / f"test_{i}.txt"
                file_path.write_text(f"content {i}")
                test_files.append(str(file_path))

            # 修复：使用异步版本的mock
            with patch.object(
                SmartInteractiveSession, "_get_user_input_async", return_value="y"
            ):
                # 1. 智能交互：确认操作
                confirmed = await smart_confirm(
                    operation="批量处理文件",
                    files_affected=test_files,
                    estimated_impact="low",
                )

                assert confirmed is True

                # 2. 性能监控：执行操作
                @PerformanceMonitor.monitor_performance("batch_file_processing")
                def process_files() -> list[str]:
                    results = []
                    for file_path in test_files:
                        try:
                            path = Path(file_path)
                            content = path.read_text()
                            results.append(f"processed: {content}")
                        except Exception as e:
                            # 3. 错误处理：统一错误管理
                            error = ToolError.from_exception(
                                e,
                                context=ErrorContext(
                                    operation="file_processing", file_path=file_path
                                ),
                            )
                            raise error
                    return results

                with patch("simple_tools.utils.performance_optimizer.logfire"):
                    results = process_files()

                    assert len(results) == 5
                    assert all("processed:" in result for result in results)
