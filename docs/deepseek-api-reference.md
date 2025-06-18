# DeepSeek API 技术参考指南

*文档版本: 1.0 | 创建日期: 2025-06-13 | 适用于: 简单工具集第三阶段*

## DeepSeek 简介

DeepSeek 是由深度求索（DeepSeek）公司开发的国产大语言模型，具有以下特点：

- **成本优势**：相比国外模型价格更低
- **中文优化**：对中文理解和生成能力强
- **开放接口**：提供标准的REST API
- **模型选择**：支持不同规模的模型

## API 接入准备

### 1. 注册和认证

1. 访问 [DeepSeek官网](https://www.deepseek.com)
2. 注册账号并完成实名认证
3. 在控制台创建API密钥
4. 记录API密钥（格式: sk-xxxxxxxxxxxxxxxx）

### 2. API 定价（参考）

| 模型 | 输入价格 | 输出价格 | 适用场景 |
|------|----------|----------|----------|
| deepseek-chat | ¥0.001/1K tokens | ¥0.002/1K tokens | 通用对话 |
| deepseek-coder | ¥0.001/1K tokens | ¥0.002/1K tokens | 代码分析 |

### 3. API 限制

- 请求频率：60次/分钟
- 单次最大tokens：32K
- 并发请求：10个

## API 调用示例

### 基础请求格式

```python
import httpx
import json

# API配置
API_KEY = "sk-your-api-key"
API_BASE = "https://api.deepseek.com/v1"

# 请求头
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 请求体
data = {
    "model": "deepseek-chat",
    "messages": [
        {
            "role": "system",
            "content": "你是一个文件分类助手。"
        },
        {
            "role": "user",
            "content": "请分析这个文件的内容并建议分类。"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 1000
}

# 发送请求
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{API_BASE}/chat/completions",
        headers=headers,
        json=data,
        timeout=30.0
    )
    result = response.json()
```

### 响应格式

```json
{
    "id": "chat-xxxxxx",
    "object": "chat.completion",
    "created": 1702438299,
    "model": "deepseek-chat",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "根据分析，这个文件应该分类为..."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 30,
        "completion_tokens": 50,
        "total_tokens": 80
    }
}
```

## 集成最佳实践

### 1. 客户端封装

```python
from typing import List, Dict, Optional
import httpx
from pydantic import BaseModel
import logfire

class DeepSeekMessage(BaseModel):
    role: str
    content: str

class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def chat_completion(
        self,
        messages: List[DeepSeekMessage],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict:
        """调用聊天完成API"""
        with logfire.span("deepseek_api_call", attributes={
            "model": model,
            "message_count": len(messages)
        }):
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": model,
                            "messages": [msg.model_dump() for msg in messages],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPError as e:
                    logfire.error(f"DeepSeek API错误: {e}")
                    raise
```

### 2. Prompt 设计原则

#### 文件分类 Prompt 模板

```python
CLASSIFY_PROMPT = """你是一个专业的文件分类助手。请根据文件内容和元数据，建议最合适的分类。

文件信息：
- 文件名：{filename}
- 文件类型：{file_type}
- 文件大小：{file_size}
- 修改时间：{modified_time}
- 内容预览：
{content_preview}

请返回JSON格式的分类建议：
{{
    "category": "分类名称",
    "confidence": 0-100的置信度,
    "reason": "分类理由"
}}

可选分类：工作文档、个人照片、系统文件、临时文件、归档文件、项目资料、学习资料、其他"""
```

#### 文档摘要 Prompt 模板

```python
SUMMARIZE_PROMPT = """请为以下文档生成一个{length}字左右的中文摘要。

文档标题：{title}
文档内容：
{content}

要求：
1. 摘要要准确概括文档的主要内容
2. 使用简洁清晰的中文表达
3. 保持客观中立的语气
4. 突出关键信息和要点

请直接返回摘要内容，不需要其他说明。"""
```

### 3. 错误处理策略

```python
from enum import Enum
from typing import Optional

class AIError(Exception):
    """AI相关错误基类"""
    pass

class APIError(AIError):
    """API调用错误"""
    pass

class RateLimitError(APIError):
    """速率限制错误"""
    pass

class TokenLimitError(APIError):
    """Token限制错误"""
    pass

async def safe_ai_call(func, *args, **kwargs):
    """安全的AI调用包装器"""
    try:
        return await func(*args, **kwargs)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RateLimitError("API调用频率超限，请稍后重试")
        elif e.response.status_code == 400:
            raise TokenLimitError("输入内容过长，请减少内容")
        else:
            raise APIError(f"API调用失败: {e}")
    except httpx.TimeoutException:
        raise APIError("API调用超时，请检查网络连接")
    except Exception as e:
        logfire.error(f"未知AI错误: {e}")
        raise AIError(f"AI功能暂时不可用: {e}")
```

### 4. 缓存机制

```python
from functools import lru_cache
import hashlib
import json
from datetime import datetime, timedelta

class AICache:
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl

    def _generate_key(self, prompt: str, **kwargs) -> str:
        """生成缓存键"""
        data = {"prompt": prompt, **kwargs}
        return hashlib.md5(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

    def get(self, prompt: str, **kwargs) -> Optional[Dict]:
        """获取缓存结果"""
        key = self._generate_key(prompt, **kwargs)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires"]:
                return entry["result"]
            else:
                del self.cache[key]
        return None

    def set(self, prompt: str, result: Dict, **kwargs):
        """设置缓存"""
        key = self._generate_key(prompt, **kwargs)
        self.cache[key] = {
            "result": result,
            "expires": datetime.now() + timedelta(seconds=self.ttl)
        }
```

### 5. 成本控制

```python
class CostTracker:
    def __init__(self, daily_limit: float = 10.0):
        self.daily_limit = daily_limit
        self.usage = {}

    def track_usage(self, tokens: int, model: str = "deepseek-chat"):
        """记录使用量"""
        today = datetime.now().date().isoformat()
        if today not in self.usage:
            self.usage[today] = {"tokens": 0, "cost": 0.0}

        # 计算成本（示例价格）
        cost_per_1k = 0.003  # ¥0.003/1K tokens
        cost = (tokens / 1000) * cost_per_1k

        self.usage[today]["tokens"] += tokens
        self.usage[today]["cost"] += cost

        # 检查限额
        if self.usage[today]["cost"] > self.daily_limit:
            raise APIError(f"已达到每日限额 ¥{self.daily_limit}")

    def get_today_usage(self) -> Dict:
        """获取今日使用情况"""
        today = datetime.now().date().isoformat()
        return self.usage.get(today, {"tokens": 0, "cost": 0.0})
```

## 测试建议

### 1. Mock 测试

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_deepseek_client():
    """测试DeepSeek客户端"""
    # Mock响应
    mock_response = {
        "choices": [{
            "message": {
                "content": '{"category": "工作文档", "confidence": 85}'
            }
        }],
        "usage": {"total_tokens": 100}
    }

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status = AsyncMock()

        client = DeepSeekClient("test-key")
        result = await client.chat_completion([
            DeepSeekMessage(role="user", content="test")
        ])

        assert result["choices"][0]["message"]["content"]
```

### 2. 集成测试

```python
# 使用真实API的集成测试（需要设置环境变量）
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要设置DEEPSEEK_API_KEY环境变量"
)
@pytest.mark.asyncio
async def test_real_api_call():
    client = DeepSeekClient(os.getenv("DEEPSEEK_API_KEY"))
    # 简单测试调用
    result = await client.chat_completion([
        DeepSeekMessage(role="user", content="Hello")
    ])
    assert result["choices"]
```

## 注意事项

1. **隐私保护**：不要发送敏感数据到API
2. **成本控制**：实现使用量监控和限额
3. **性能优化**：合理使用缓存减少API调用
4. **错误处理**：API不可用时要能优雅降级
5. **日志记录**：记录所有API调用便于调试

## 参考链接

- [DeepSeek官方文档](https://platform.deepseek.com/docs)
- [API调用示例](https://github.com/deepseek-ai/deepseek-sdk)
- [定价说明](https://platform.deepseek.com/pricing)

---

**提醒**：在正式使用前，请先用少量请求测试API的稳定性和响应速度！
