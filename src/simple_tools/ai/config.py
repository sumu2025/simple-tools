"""AI配置管理模块"""

import os
from typing import Optional

import logfire
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIConfig(BaseSettings):
    """AI配置模型

    Attributes:
        enabled: 是否启用AI功能
        provider: AI服务提供商
        api_key: API密钥
        api_base: API基础URL
        model: 默认使用的模型
        max_tokens: 最大生成token数
        temperature: 生成温度
        timeout: API调用超时时间
        cache_ttl: 缓存有效期（秒）
        daily_limit: 每日费用限额（元）
        monthly_limit: 每月费用限额（元）
        smart_classify: 智能文件分类功能开关
        auto_summarize: 文档自动摘要功能开关
        content_analysis: 内容智能分析功能开关

    """

    # Pydantic V2 推荐的配置方式
    model_config = SettingsConfigDict(
        env_prefix="DEEPSEEK_",  # 环境变量前缀
        extra="ignore",
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    enabled: bool = Field(False, description="是否启用AI功能")
    provider: str = Field("deepseek", description="AI服务提供商")
    api_key: Optional[SecretStr] = Field(None, description="API密钥")
    api_base: str = Field(
        "https://api.deepseek.com/v1", description="官方推荐 DeepSeek 基础URL"
    )
    model: str = Field("deepseek-chat", description="默认使用的模型")
    max_tokens: int = Field(1000, description="最大生成token数")
    temperature: float = Field(0.7, description="生成温度")
    timeout: float = Field(60.0, description="API调用超时时间")
    cache_ttl: int = Field(3600, description="缓存有效期（秒）")

    # 成本控制
    daily_limit: float = Field(10.0, description="每日费用限额（元）")
    monthly_limit: float = Field(300.0, description="每月费用限额（元）")

    # 功能开关
    smart_classify: bool = Field(True, description="智能文件分类")
    auto_summarize: bool = Field(True, description="文档自动摘要")
    content_analysis: bool = Field(True, description="内容智能分析")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_configured(self) -> bool:
        """检查是否已配置API密钥"""
        return bool(self.api_key)


def get_ai_config() -> AIConfig:
    """获取AI配置实例

    优先级：
    1. 环境变量 (以 DEEPSEEK_ 开头，例如 DEEPSEEK_API_KEY)
    2. （如果实现了）配置文件
    3. 模型定义的默认值

    Returns:
        AIConfig: AI配置实例

    """
    # BaseSettings 会自动从环境变量加载配置
    # 我们只需要处理那些不直接通过 env_prefix 映射的特殊环境变量
    # 例如 'SIMPLE_TOOLS_AI_ENABLED'

    env_vars_to_check = {}
    ai_enabled_env = os.getenv("SIMPLE_TOOLS_AI_ENABLED")
    if ai_enabled_env is not None:
        env_vars_to_check["enabled"] = ai_enabled_env.lower() == "true"

    # 创建配置实例，BaseSettings 会自动加载 DEEPSEEK_* 环境变量
    # 然后用 env_vars_to_check 中的值覆盖（如果存在）
    config = AIConfig(**env_vars_to_check)  # type: ignore

    logfire.info(
        "AI配置加载完成",
        enabled=config.enabled,
        is_configured=config.is_configured,
        provider=config.provider,
        model=config.model,
    )

    return config
