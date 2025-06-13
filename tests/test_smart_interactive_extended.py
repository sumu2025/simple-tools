"""额外的智能交互系统测试。

覆盖更多功能和边缘情况。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from simple_tools.utils.smart_interactive import (
    CommandSuggestionEngine,
    ConfirmationRequest,
    InteractionContext,
    OperationHistory,
    SmartInteractiveSession,
    UserResponse,
    _is_test_environment,
    smart_confirm_sync,
)


class TestCommandSuggestionEngineExtended:
    """测试命令建议引擎的额外功能。"""

    def test_show_help_with_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试显示帮助信息（带错误）。"""
        engine = CommandSuggestionEngine()
        engine.show_help("lst", "命令 'lst' 不存在")

        captured = capsys.readouterr()
        assert "❌ 命令 'lst' 不存在" in captured.out
        assert "您是否想要使用以下命令" in captured.out
        assert "list" in captured.out
        assert "可用命令" in captured.out

    def test_show_help_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试显示帮助信息（无错误）。"""
        engine = CommandSuggestionEngine()
        engine.show_help("org")

        captured = capsys.readouterr()
        assert "您是否想要使用以下命令" in captured.out
        assert "organize" in captured.out

    def test_add_to_history(self) -> None:
        """测试添加命令到历史记录。"""
        engine = CommandSuggestionEngine()

        # 添加命令
        engine.add_to_history("list")
        engine.add_to_history("duplicates")
        engine.add_to_history("list")  # 重复命令不应重复添加

        assert engine.command_history == ["list", "duplicates"]

    def test_history_size_limit(self) -> None:
        """测试历史记录大小限制。"""
        engine = CommandSuggestionEngine()

        # 添加超过50个命令
        for i in range(60):
            engine.add_to_history(f"command_{i}")

        # 应该只保留最后50个
        assert len(engine.command_history) == 50
        assert engine.command_history[0] == "command_10"
        assert engine.command_history[-1] == "command_59"

    def test_get_similarity_score(self) -> None:
        """测试相似度计算。"""
        engine = CommandSuggestionEngine()

        # 测试缓存效果（多次调用应该使用缓存）
        score1 = engine.get_similarity_score("list", "lst")
        score2 = engine.get_similarity_score("list", "lst")

        assert score1 == score2
        assert 0.5 < score1 < 1.0


class TestIsTestEnvironment:
    """测试环境检测函数。"""

    def test_pytest_environment(self) -> None:
        """测试pytest环境检测。"""
        # 当前在pytest中运行，应该返回True
        assert _is_test_environment() is True

    def test_other_test_environments(self) -> None:
        """测试其他测试环境检测。"""
        with patch.dict(os.environ, {"TESTING": "true"}):
            assert _is_test_environment() is True

        # 模拟unittest环境
        with patch.dict("sys.modules", {"unittest": MagicMock()}):
            assert _is_test_environment() is True


class TestOperationHistory:
    """测试操作历史记录。"""

    @pytest.fixture
    def temp_history_file(self) -> Path:
        """创建临时历史文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / ".simple-tools" / "history.json"
            history_file.parent.mkdir(exist_ok=True)

            def mock_init(self: OperationHistory) -> None:
                self.history_file = history_file
                self.max_records = 100

            with patch.object(
                OperationHistory,
                "__init__",
                mock_init,
            ):
                yield history_file

    def test_add_and_get_history(self, temp_history_file: Path) -> None:
        """测试添加和获取历史记录。"""
        history = OperationHistory()

        # 添加记录
        history.add("list", {"path": "/tmp"}, {"files": 10})
        history.add("duplicates", {"path": "/home"}, {"found": 5})

        # 获取记录
        records = history.get_recent(2)
        assert len(records) == 2
        assert records[0]["command"] == "list"
        assert records[1]["command"] == "duplicates"

    def test_show_recent_empty(
        self, temp_history_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试显示空历史记录。"""
        history = OperationHistory()
        history.show_recent()

        captured = capsys.readouterr()
        assert "暂无操作记录" in captured.out

    def test_show_recent_with_records(
        self, temp_history_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试显示历史记录。"""
        history = OperationHistory()

        # 添加记录
        history.add("list", {"path": "/tmp"}, {"files": 10})

        # 显示记录
        history.show_recent(1)

        captured = capsys.readouterr()
        assert "最近 1 条操作记录" in captured.out
        assert "list" in captured.out
        assert "path" in captured.out
        assert "files" in captured.out

    def test_clear_history(self, temp_history_file: Path) -> None:
        """测试清空历史记录。"""
        history = OperationHistory()

        # 添加记录
        history.add("list", {}, {})
        assert len(history.get_recent()) == 1

        # 清空
        history.clear()
        assert len(history.get_recent()) == 0

    def test_history_size_limit(self, temp_history_file: Path) -> None:
        """测试历史记录大小限制。"""
        history = OperationHistory()
        history.max_records = 5  # 设置较小的限制便于测试

        # 添加超过限制的记录
        for i in range(10):
            history.add(f"command_{i}", {}, {})

        records = history.get_recent(10)
        assert len(records) == 5
        assert records[0]["command"] == "command_5"
        assert records[-1]["command"] == "command_9"

    def test_load_corrupted_history(self, temp_history_file: Path) -> None:
        """测试加载损坏的历史文件。"""
        history = OperationHistory()

        # 写入损坏的JSON
        with open(history.history_file, "w") as f:
            f.write("corrupted json{")

        # 应该返回空列表而不是崩溃
        records = history._load()
        assert records == []


class TestSmartInteractiveSessionExtended:
    """测试智能交互会话的额外功能。"""

    def test_interaction_context(self) -> None:
        """测试交互上下文。"""
        context = InteractionContext(
            session_id="test_session", operation_type="test_op"
        )

        # 等待一小段时间
        import time

        time.sleep(0.1)

        assert context.session_duration > 0.09

    def test_user_response_decision_speed(self) -> None:
        """测试用户响应速度分类。"""
        # 即时响应
        response1 = UserResponse(decision=True, response_time=1.5)
        assert response1.decision_speed == "instant"

        # 快速响应
        response2 = UserResponse(decision=True, response_time=3.0)
        assert response2.decision_speed == "quick"

        # 考虑响应
        response3 = UserResponse(decision=True, response_time=7.0)
        assert response3.decision_speed == "considered"

        # 深思熟虑
        response4 = UserResponse(decision=False, response_time=15.0)
        assert response4.decision_speed == "deliberate"

    def test_confirmation_request_edge_cases(self) -> None:
        """测试确认请求的边缘情况。"""
        # 大规模操作
        request = ConfirmationRequest(
            operation="批量处理",
            files_affected=[f"file_{i}" for i in range(150)],
            estimated_impact="low",
        )

        risk = request.risk_assessment
        assert risk["level"] == "critical"
        assert risk["score"] == 8

    def test_smart_confirm_sync(self) -> None:
        """测试同步版本的智能确认。"""
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = True

            result = smart_confirm_sync(
                operation="测试操作", files_affected=["test.txt"]
            )

            assert result is True
            mock_run.assert_called_once()

    def test_smart_confirm_sync_keyboard_interrupt(self) -> None:
        """测试同步确认时的键盘中断。"""
        with patch("asyncio.run") as mock_run:
            mock_run.side_effect = KeyboardInterrupt()

            result = smart_confirm_sync(operation="测试操作")

            assert result is False

    def test_parse_user_decision_various_inputs(self) -> None:
        """测试解析各种用户输入。"""
        session = SmartInteractiveSession()

        # 测试各种肯定输入
        assert session._parse_user_decision("y") is True
        assert session._parse_user_decision("YES") is True
        assert session._parse_user_decision("是") is True
        assert session._parse_user_decision("确认") is True
        assert session._parse_user_decision("1") is True
        assert session._parse_user_decision("true") is True
        assert session._parse_user_decision("  y  ") is True

        # 测试否定输入
        assert session._parse_user_decision("n") is False
        assert session._parse_user_decision("no") is False
        assert session._parse_user_decision("") is False
        assert session._parse_user_decision("maybe") is False


class TestConfirmationRequestRiskAssessment:
    """测试风险评估的各种情况。"""

    def test_high_impact_many_files(self) -> None:
        """测试高影响+多文件。"""
        request = ConfirmationRequest(
            operation="删除",
            files_affected=[f"file_{i}" for i in range(20)],
            estimated_impact="high",
        )

        risk = request.risk_assessment
        assert risk["level"] == "critical"
        assert risk["score"] == 9

    def test_medium_impact_moderate_files(self) -> None:
        """测试中等影响+中等文件数。"""
        request = ConfirmationRequest(
            operation="重命名",
            files_affected=[f"file_{i}" for i in range(8)],
            estimated_impact="medium",
        )

        risk = request.risk_assessment
        assert risk["level"] == "warning"
        assert risk["score"] == 6

    def test_many_changes(self) -> None:
        """测试大量变更。"""
        changes = {f"old_{i}": f"new_{i}" for i in range(60)}
        request = ConfirmationRequest(operation="替换", preview_changes=changes)

        risk = request.risk_assessment
        assert risk["level"] == "critical"
        assert risk["score"] == 8


# 全局实例测试
def test_global_instances() -> None:
    """测试全局实例。"""
    from simple_tools.utils.smart_interactive import (
        command_suggester,
        operation_history,
    )

    assert isinstance(command_suggester, CommandSuggestionEngine)
    assert isinstance(operation_history, OperationHistory)
