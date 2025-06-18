"""测试错误处理路径以提升覆盖率"""

import os
from pathlib import Path

from simple_tools.core.file_organizer import FileOrganizerTool, OrganizeConfig
from simple_tools.core.text_replace import ReplaceConfig, TextReplaceTool
from simple_tools.utils.errors import (
    BatchErrorCollector,
    ErrorContext,
    ToolError,
    format_friendly_error,
)


class TestErrorHandlingPaths:
    """测试各种错误处理路径"""

    def test_batch_error_collector_edge_cases(self) -> None:
        """测试批量错误收集器的边界情况"""
        collector = BatchErrorCollector("测试操作")

        # 测试空错误列表
        assert not collector.has_errors()
        assert collector.success_count == 0

        # 添加成功记录
        collector.record_success()
        collector.record_success()
        assert collector.success_count == 2

        # 添加错误
        error1 = ValueError("错误1")
        error2 = ToolError("错误2", "TEST_ERROR")

        collector.record_error("file1.txt", error1)
        collector.record_error("file2.txt", error2)

        assert collector.has_errors()
        assert len(collector.errors) == 2

        # 测试格式化输出
        summary = collector.format_summary()
        assert "Success: 2" in summary
        assert "Failed: 2" in summary
        assert "ValueError" in summary
        assert "ToolError" in summary  # 注意：显示的是错误类型名，不是错误代码

    def test_tool_error_with_original_error(self) -> None:
        """测试带原始错误的 ToolError"""
        original = ValueError("原始错误")
        error = ToolError(
            "包装的错误",
            "WRAPPED_ERROR",
            original_error=original,
            suggestions=["建议1", "建议2"],
        )

        formatted = error.format_message()
        assert "包装的错误" in formatted
        # 注意：error_code 不会出现在格式化消息中
        assert "建议1" in formatted
        assert "建议2" in formatted
        assert error.error_code == "WRAPPED_ERROR"  # 检查属性而不是格式化输出

    def test_file_organizer_error_paths(self, tmp_path: Path) -> None:
        """测试文件整理工具的错误路径"""
        # 测试无权限的情况
        protected_dir = tmp_path / "protected"
        protected_dir.mkdir()

        # 创建一个文件
        test_file = protected_dir / "test.txt"
        test_file.write_text("test")

        # 创建配置
        config = OrganizeConfig(path=str(protected_dir), mode="type", dry_run=False)

        organizer = FileOrganizerTool(config)

        # 获取整理计划
        items = organizer.create_organize_plan()

        # 模拟权限错误
        if os.name != "nt":  # 非 Windows 系统
            # 设置目录为只读
            protected_dir.chmod(0o444)

            try:
                # 尝试执行整理（应该失败）
                result = organizer.execute_organize(items)
                # 应该有失败的文件
                assert result.failed > 0 or result.skipped > 0
            finally:
                # 恢复权限
                protected_dir.chmod(0o755)

    def test_text_replace_permission_error(self, tmp_path: Path) -> None:
        """测试文本替换的权限错误"""
        # 创建只读文件
        read_only_file = tmp_path / "readonly.txt"
        read_only_file.write_text("TODO: test")

        if os.name != "nt":  # 非 Windows 系统
            # 设置文件为只读
            read_only_file.chmod(0o444)

            try:
                config = ReplaceConfig(
                    pattern="TODO:DONE", file=str(read_only_file), dry_run=False
                )

                tool = TextReplaceTool(config)
                result = tool.replace_in_file(read_only_file)

                # 应该有错误
                assert result.error == "没有写入权限"
                assert not result.replaced
            finally:
                # 恢复权限
                read_only_file.chmod(0o644)

    def test_error_context_edge_cases(self) -> None:
        """测试错误上下文的边界情况"""
        # 测试最小上下文（operation 是必需字段）
        context = ErrorContext(operation="默认操作")
        assert context.operation == "默认操作"
        assert context.file_path is None
        assert context.details == {}  # 默认为空字典

        # 测试完整上下文
        context = ErrorContext(
            operation="测试操作",
            file_path="/test/path",
            details={"key": "value", "count": 42},
        )
        assert context.operation == "测试操作"
        assert context.file_path == "/test/path"
        assert context.details["count"] == 42

        # 测试 details 为 None 的情况
        context = ErrorContext(operation="测试", details=None)
        assert context.details == {}  # 应该转换为空字典

    def test_format_friendly_error_with_context(self) -> None:
        """测试友好错误格式化"""
        context = ErrorContext(
            operation="测试操作", file_path="/test/path", details={"key": "value"}
        )

        error = ToolError(
            "测试错误",
            "TEST_ERROR",
            context=context,
            suggestions=["建议1", "建议2", "建议3"],
        )

        formatted = format_friendly_error(error)
        assert "测试错误" in formatted
        # error_code 不会显示在格式化输出中
        assert "/test/path" in formatted
        assert "建议1" in formatted
        assert "建议2" in formatted
        assert "建议3" in formatted
