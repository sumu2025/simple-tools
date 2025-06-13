"""智能交互系统单元测试.

测试覆盖：确认对话、命令建议、风险评估、异步操作.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from simple_tools.utils.smart_interactive import (
    CommandSuggestionEngine,
    ConfirmationRequest,
    SmartInteractiveSession,
    UserResponse,
    smart_confirm,
)


class TestConfirmationRequest:
    """测试确认请求模型"""

    def test_risk_assessment_critical(self) -> None:
        """测试高风险评估"""
        request = ConfirmationRequest(
            operation="批量删除",
            files_affected=[f"file_{i}.txt" for i in range(15)],
            estimated_impact="high",
        )

        risk = request.risk_assessment
        assert risk["level"] == "critical"
        assert risk["score"] == 9
        assert "🚨" in risk["message"]

    def test_risk_assessment_safe(self) -> None:
        """测试安全操作评估"""
        request = ConfirmationRequest(
            operation="格式化代码", files_affected=["main.py"], estimated_impact="low"
        )

        risk = request.risk_assessment
        assert risk["level"] == "safe"
        assert risk["score"] == 2
        assert "✅" in risk["message"]


class TestCommandSuggestionEngine:
    """测试命令建议引擎"""

    def test_suggest_similar_commands(self) -> None:
        """测试相似命令建议"""
        engine = CommandSuggestionEngine()
        suggestions = engine.suggest_commands("ren")

        assert len(suggestions) > 0
        # 检查是否有rename命令的建议
        assert any(s["command"] == "rename" for s in suggestions)
        assert all(s["score"] > 0.3 for s in suggestions)

    def test_no_suggestions_for_empty_input(self) -> None:
        """测试空输入无建议"""
        engine = CommandSuggestionEngine()
        suggestions = engine.suggest_commands("")
        assert len(suggestions) == 0


class TestSmartInteractiveSession:
    """测试智能交互会话"""

    @pytest.mark.asyncio
    async def test_async_confirm_accept(self) -> None:
        """测试异步确认 - 接受"""
        session = SmartInteractiveSession()
        request = ConfirmationRequest(operation="测试操作", files_affected=["test.txt"])

        with patch.object(
            session, "_get_user_input_async", new_callable=AsyncMock, return_value="y"
        ):
            response = await session.smart_confirm_async(request)
            assert response.decision is True
            assert response.response_time > 0

    @pytest.mark.asyncio
    async def test_async_confirm_timeout(self) -> None:
        """测试异步确认超时"""
        session = SmartInteractiveSession()
        request = ConfirmationRequest(operation="测试操作")

        # 模拟超时
        with patch.object(
            session, "_get_user_input_async", side_effect=asyncio.TimeoutError()
        ):
            response = await session.smart_confirm_async(request, timeout=0.1)
            assert response.decision is False


@pytest.mark.asyncio
async def test_smart_confirm_convenience_function() -> None:
    """测试便捷确认函数"""
    with patch(
        "simple_tools.utils.smart_interactive.SmartInteractiveSession"
    ) as mock_session:
        mock_instance = mock_session.return_value
        mock_instance.smart_confirm_async = AsyncMock(
            return_value=UserResponse(decision=True, response_time=1.0)
        )

        result = await smart_confirm(operation="测试操作", files_affected=["test.txt"])

        assert result is True
        mock_instance.smart_confirm_async.assert_called_once()
