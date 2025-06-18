"""AI模块单元测试"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from simple_tools.ai import DeepSeekClient, get_ai_config
from simple_tools.ai.config import AIConfig
from simple_tools.ai.deepseek_client import (
    AICache,
    CostTracker,
    DeepSeekMessage,
    DeepSeekResponse,
)
from simple_tools.ai.prompts import PromptManager
from simple_tools.utils.errors import ToolError


class TestAIConfig:
    """AI配置测试"""

    def test_default_config(self) -> None:
        """测试默认配置"""
        config = AIConfig()
        assert config.enabled is False
        assert config.provider == "deepseek"
        assert config.model == "deepseek-chat"
        assert config.daily_limit == 10.0

    def test_config_from_env(self) -> None:
        """测试从环境变量读取配置"""
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "test-key",
                "SIMPLE_TOOLS_AI_ENABLED": "true",
            },
        ):
            config = get_ai_config()
            assert config.api_key.get_secret_value() == "test-key"
            assert config.enabled is True
            assert config.is_configured is True


class TestPromptManager:
    """Prompt管理器测试"""

    def test_get_template(self) -> None:
        """测试获取模板"""
        template = PromptManager.get("file_classify")
        assert template is not None

    def test_format_template(self) -> None:
        """测试格式化模板"""
        formatted = PromptManager.format(
            "file_classify",
            filename="test.txt",
            extension=".txt",
            file_size="1KB",
            modified_time="2025-01-01",
            content_preview="Hello",
        )
        assert "test.txt" in formatted
        assert ".txt" in formatted

    def test_unknown_template(self) -> None:
        """测试获取不存在的模板"""
        with pytest.raises(ValueError):
            PromptManager.get("unknown_template")


class TestAICache:
    """AI缓存测试"""

    def test_cache_miss(self) -> None:
        """测试缓存未命中"""
        cache = AICache(ttl=3600)
        messages = [DeepSeekMessage(role="user", content="test")]
        result = cache.get(messages)
        assert result is None

    def test_cache_hit(self) -> None:
        """测试缓存命中"""
        cache = AICache(ttl=3600)
        messages = [DeepSeekMessage(role="user", content="test")]
        response = DeepSeekResponse(content="response", usage={})

        # 设置缓存
        cache.set(messages, response)

        # 获取缓存
        cached = cache.get(messages)
        assert cached is not None
        assert cached.content == "response"

    def test_cache_expiration(self) -> None:
        """测试缓存过期"""
        cache = AICache(ttl=1)  # 1秒过期
        messages = [DeepSeekMessage(role="user", content="test")]
        response = DeepSeekResponse(content="response", usage={})

        # 设置缓存
        cache.set(messages, response)

        # 模拟时间流逝
        with patch("simple_tools.ai.deepseek_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)
            cached = cache.get(messages)
            assert cached is None


class TestCostTracker:
    """成本追踪器测试"""

    def test_track_usage(self) -> None:
        """测试使用量追踪"""
        tracker = CostTracker()
        cost = tracker.track("deepseek-chat", prompt_tokens=100, completion_tokens=50)

        assert cost["total_cost"] > 0
        usage = tracker.get_today_usage()
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["requests"] == 1

    def test_check_limit(self) -> None:
        """测试限额检查"""
        tracker = CostTracker()

        # 模拟超出限额
        tracker.usage[datetime.now().date().isoformat()] = {
            "total_cost": 20.0,
            "requests": 100,
        }

        with pytest.raises(ToolError) as exc_info:
            tracker.check_limit(10.0)
        assert exc_info.value.error_code == "AI_QUOTA_EXCEEDED"


class TestDeepSeekClient:
    """DeepSeek客户端测试"""

    def test_client_without_api_key(self) -> None:
        """测试没有API密钥时的初始化"""
        config = AIConfig(api_key=None)
        with pytest.raises(ToolError) as exc_info:
            DeepSeekClient(config)
        assert exc_info.value.error_code == "AI_NOT_CONFIGURED"

    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_successful_chat(self, mock_post: MagicMock) -> None:
        """测试成功的聊天调用"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            "model": "deepseek-chat",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # 创建客户端并调用
        config = AIConfig(api_key="test-key")
        client = DeepSeekClient(config)
        messages = [DeepSeekMessage(role="user", content="Hi")]

        response = await client.chat_completion(messages, use_cache=False)

        assert response.content == "Hello!"
        assert response.usage["total_tokens"] == 15

    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_post: MagicMock) -> None:
        """测试API错误处理"""
        # 模拟429错误（速率限制）
        mock_http_response = MagicMock(spec=httpx.Response)
        mock_http_response.status_code = 429
        mock_http_response.request = MagicMock(spec=httpx.Request)
        # Ensure the mock_post returns an object that has a raise_for_status method
        mock_api_response = MagicMock()
        mock_api_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Rate limit exceeded",
            request=mock_http_response.request,
            response=mock_http_response,
        )
        mock_post.return_value = mock_api_response

        config = AIConfig(api_key="test-key")
        client = DeepSeekClient(config)
        messages = [DeepSeekMessage(role="user", content="Hi")]

        with pytest.raises(ToolError) as exc_info:
            await client.chat_completion(messages, use_cache=False)
        assert exc_info.value.error_code == "AI_RATE_LIMIT"

    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_api_bad_request(self, mock_post: MagicMock) -> None:
        """测试API 400错误处理"""
        mock_http_response = MagicMock(spec=httpx.Response)
        mock_http_response.status_code = 400
        mock_http_response.request = MagicMock(spec=httpx.Request)
        mock_http_response.json.return_value = {"error": {"message": "Invalid request"}}
        mock_api_response = MagicMock()
        mock_api_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Bad request",
            request=mock_http_response.request,
            response=mock_http_response,
        )
        mock_post.return_value = mock_api_response

        config = AIConfig(api_key="test-key")
        client = DeepSeekClient(config)
        with pytest.raises(ToolError) as exc_info:
            await client.chat_completion([DeepSeekMessage(role="user", content="Hi")])
        assert exc_info.value.error_code == "AI_BAD_REQUEST"
        assert "Invalid request" in str(exc_info.value)

    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_api_auth_failed(self, mock_post: MagicMock) -> None:
        """测试API 401错误处理"""
        mock_http_response = MagicMock(spec=httpx.Response)
        mock_http_response.status_code = 401
        mock_http_response.request = MagicMock(spec=httpx.Request)
        mock_api_response = MagicMock()
        mock_api_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Auth failed",
            request=mock_http_response.request,
            response=mock_http_response,
        )
        mock_post.return_value = mock_api_response

        config = AIConfig(api_key="invalid-key")
        client = DeepSeekClient(config)
        with pytest.raises(ToolError) as exc_info:
            await client.chat_completion([DeepSeekMessage(role="user", content="Hi")])
        assert exc_info.value.error_code == "AI_AUTH_FAILED"

    @patch("httpx.AsyncClient.post")
    @pytest.mark.asyncio
    async def test_api_generic_error(self, mock_post: MagicMock) -> None:
        """测试API通用HTTP错误处理"""
        mock_http_response = MagicMock(spec=httpx.Response)
        mock_http_response.status_code = 500  # Internal Server Error
        mock_http_response.request = MagicMock(spec=httpx.Request)
        mock_api_response = MagicMock()
        mock_api_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Server error",
            request=mock_http_response.request,
            response=mock_http_response,
        )
        mock_post.return_value = mock_api_response

        config = AIConfig(api_key="test-key")
        client = DeepSeekClient(config)
        with pytest.raises(ToolError) as exc_info:
            await client.chat_completion([DeepSeekMessage(role="user", content="Hi")])
        assert exc_info.value.error_code == "AI_API_ERROR"
        assert "HTTP 500" in str(exc_info.value)

    @patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout"))
    @pytest.mark.asyncio
    async def test_api_timeout(self, mock_post: MagicMock) -> None:
        """测试API超时错误处理"""
        config = AIConfig(api_key="test-key")
        client = DeepSeekClient(config)
        with pytest.raises(ToolError) as exc_info:
            await client.chat_completion([DeepSeekMessage(role="user", content="Hi")])
        assert exc_info.value.error_code == "AI_TIMEOUT"

    @patch("httpx.AsyncClient.post", side_effect=Exception("Generic network error"))
    @pytest.mark.asyncio
    async def test_api_unknown_error(self, mock_post: MagicMock) -> None:
        """测试API未知网络错误处理"""
        config = AIConfig(api_key="test-key")
        client = DeepSeekClient(config)
        with pytest.raises(ToolError) as exc_info:
            await client.chat_completion([DeepSeekMessage(role="user", content="Hi")])
        assert exc_info.value.error_code == "AI_UNKNOWN_ERROR"
        assert "Generic network error" in str(exc_info.value)

    @patch("simple_tools.ai.deepseek_client.DeepSeekClient.chat_completion")
    @pytest.mark.asyncio
    async def test_simple_chat(self, mock_chat_completion: MagicMock) -> None:
        """测试简化聊天接口"""
        mock_chat_completion.return_value = DeepSeekResponse(content="Simple response")
        client = DeepSeekClient(AIConfig(api_key="test-key"))
        response = await client.simple_chat("Hello", system_prompt="Be friendly")
        assert response == "Simple response"
        mock_chat_completion.assert_called_once_with(
            [
                DeepSeekMessage(role="system", content="Be friendly"),
                DeepSeekMessage(role="user", content="Hello"),
            ]
        )

    def test_get_usage_stats(self) -> None:
        """测试获取使用统计"""
        config = AIConfig(api_key="test-key", model="test-model", daily_limit=100.0)
        client = DeepSeekClient(config)
        client.cost_tracker.usage = {"2023-01-01": {"total_cost": 50.0}}
        client.cache.cache = {"key1": {}, "key2": {}}
        stats = client.get_usage_stats()
        assert stats["today"] == client.cost_tracker.get_today_usage()
        assert stats["cache_size"] == 2
        assert stats["model"] == "test-model"
        assert stats["daily_limit"] == 100.0
