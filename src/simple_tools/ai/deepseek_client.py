"""DeepSeek API客户端

提供与DeepSeek API交互的客户端实现，包括：
- API调用封装
- 错误处理
- 重试机制
- 响应缓存
- 成本统计
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, NoReturn, Optional

import httpx
import logfire
from pydantic import BaseModel, Field

from ..utils.errors import ToolError
from .config import AIConfig, get_ai_config


class DeepSeekMessage(BaseModel):
    """DeepSeek消息模型"""

    role: str = Field(..., description="角色：system/user/assistant")
    content: str = Field(..., description="消息内容")


class DeepSeekResponse(BaseModel):
    """DeepSeek响应模型"""

    content: str = Field(..., description="生成的内容")
    usage: dict[str, Any] = Field(default_factory=dict, description="token使用情况")
    model: str = Field("", description="使用的模型")
    finish_reason: str = Field("", description="结束原因")


class AICache:
    """AI响应缓存"""

    def __init__(self, ttl: int = 3600):
        """初始化缓存实例

        Args:
            ttl: 缓存存活时间（秒）

        """
        self.cache: dict[str, dict[str, Any]] = {}
        self.ttl = ttl

    def _generate_key(self, messages: list[DeepSeekMessage], **kwargs: Any) -> str:
        """生成缓存键"""
        data = {
            "messages": [msg.model_dump() for msg in messages],
            **kwargs,
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def get(
        self, messages: list[DeepSeekMessage], **kwargs: Any
    ) -> Optional[DeepSeekResponse]:
        """获取缓存的响应"""
        key = self._generate_key(messages, **kwargs)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires"]:
                logfire.info("使用缓存的AI响应", attributes={"cache_key": key})
                return DeepSeekResponse(**entry["response"])
            else:
                del self.cache[key]
        return None

    def set(
        self, messages: list[DeepSeekMessage], response: DeepSeekResponse, **kwargs: Any
    ) -> None:
        """缓存响应"""
        key = self._generate_key(messages, **kwargs)
        self.cache[key] = {
            "response": response.model_dump(),
            "expires": datetime.now() + timedelta(seconds=self.ttl),
        }


class CostTracker:
    """成本追踪器"""

    # DeepSeek定价（示例，实际价格请参考官方）
    PRICING = {
        "deepseek-chat": {"input": 0.001, "output": 0.002},  # 元/1K tokens
        "deepseek-coder": {"input": 0.001, "output": 0.002},
        "deepseek-reasoner": {"input": 0.001, "output": 0.002},  # reasoner模型
    }

    def __init__(self) -> None:
        """初始化成本追踪器"""
        self.usage: dict[str, dict[str, Any]] = {}

    def track(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> dict[str, float]:
        """记录使用量并计算成本"""
        today = datetime.now().date().isoformat()
        if today not in self.usage:
            self.usage[today] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0,
                "requests": 0,
            }

        # 计算成本
        pricing = self.PRICING.get(model, self.PRICING["deepseek-chat"])
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost

        # 更新统计
        self.usage[today]["prompt_tokens"] += prompt_tokens
        self.usage[today]["completion_tokens"] += completion_tokens
        self.usage[today]["total_cost"] += total_cost
        self.usage[today]["requests"] += 1

        logfire.info(
            "AI使用量统计",
            attributes={
                "date": today,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": total_cost,
            },
        )

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }

    def get_today_usage(self) -> dict[str, Any]:
        """获取今日使用情况"""
        today = datetime.now().date().isoformat()
        return self.usage.get(
            today,
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0,
                "requests": 0,
            },
        )

    def check_limit(self, daily_limit: float) -> None:
        """检查是否超过限额"""
        today_usage = self.get_today_usage()
        if today_usage["total_cost"] > daily_limit:
            raise ToolError(
                f"已超过每日AI使用限额（¥{daily_limit}）", "AI_QUOTA_EXCEEDED"
            )


class DeepSeekClient:
    """DeepSeek API客户端"""

    def __init__(self, config: Optional[AIConfig] = None) -> None:
        """初始化客户端

        Args:
            config: AI配置对象，默认自动获取

        """
        self.config = config or get_ai_config()
        if not self.config.api_key:
            raise ToolError(
                "未配置DeepSeek API密钥，请设置DEEPSEEK_API_KEY环境变量",
                "AI_NOT_CONFIGURED",
            )

        self.headers = {
            "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        self.cache = AICache(ttl=self.config.cache_ttl)
        self.cost_tracker: CostTracker = CostTracker()

    async def chat_completion(
        self,
        messages: list[DeepSeekMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> DeepSeekResponse:
        """调用聊天完成API

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 生成温度
            max_tokens: 最大token数
            use_cache: 是否使用缓存

        Returns:
            DeepSeekResponse: API响应

        Raises:
            ToolError: API调用失败

        """
        model = model or self.config.model
        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens

        # 检查每日限额
        self.cost_tracker.check_limit(self.config.daily_limit)

        # 尝试从缓存获取
        if use_cache:
            cached = self.cache.get(
                messages, model=model, temperature=temperature, max_tokens=max_tokens
            )
            if cached:
                return cached

        # 准备请求数据
        request_data = {
            "model": model,
            "messages": [msg.model_dump() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 发送请求
        with logfire.span(
            "deepseek_api_call",
            attributes={
                "model": model,
                "message_count": len(messages),
                "max_tokens": max_tokens,
            },
        ):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.config.api_base}/chat/completions",
                        headers=self.headers,
                        json=request_data,
                        timeout=self.config.timeout,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # 解析响应
                    choice = data["choices"][0]
                    usage = data.get("usage", {})

                    result = DeepSeekResponse(
                        content=choice["message"]["content"],
                        usage=usage,
                        model=data.get("model", model),
                        finish_reason=choice.get("finish_reason", ""),
                    )

                    # 记录成本
                    if usage:
                        self.cost_tracker.track(
                            model,
                            usage.get("prompt_tokens", 0),
                            usage.get("completion_tokens", 0),
                        )

                    # 缓存结果
                    if use_cache:
                        self.cache.set(
                            messages,
                            result,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )

                    return result

            except httpx.HTTPStatusError as e:
                self._handle_api_error(e)

            except httpx.TimeoutException:
                raise ToolError("API调用超时，请检查网络连接", "AI_TIMEOUT")

            except Exception as e:
                logfire.error(f"DeepSeek API未知错误: {e}")
                raise ToolError(f"AI功能暂时不可用：{str(e)}", "AI_UNKNOWN_ERROR")

    def _handle_api_error(self, e: httpx.HTTPStatusError) -> NoReturn:
        """处理API错误响应"""
        if e.response.status_code == 429:
            raise ToolError("API调用频率超限，请稍后重试", "AI_RATE_LIMIT")
        if e.response.status_code == 400:
            error_data = e.response.json()
            error_msg = error_data.get("error", {}).get("message", "请求参数错误")
            raise ToolError(f"API请求错误：{error_msg}", "AI_BAD_REQUEST")
        if e.response.status_code == 401:
            raise ToolError("API密钥无效或已过期", "AI_AUTH_FAILED")
        raise ToolError(f"API调用失败：HTTP {e.response.status_code}", "AI_API_ERROR")

    async def simple_chat(self, prompt: str, system_prompt: str = "") -> str:
        """简化的聊天接口

        Args:
            prompt: 用户提示
            system_prompt: 系统提示

        Returns:
            str: AI生成的响应文本

        """
        messages = []
        if system_prompt:
            messages.append(DeepSeekMessage(role="system", content=system_prompt))
        messages.append(DeepSeekMessage(role="user", content=prompt))

        response = await self.chat_completion(messages)
        return response.content

    def get_usage_stats(self) -> dict[str, Any]:
        """获取使用统计"""
        return {
            "today": self.cost_tracker.get_today_usage(),
            "cache_size": len(self.cache.cache),
            "model": self.config.model,
            "daily_limit": self.config.daily_limit,
        }
