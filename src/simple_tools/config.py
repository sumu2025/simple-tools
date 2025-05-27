"""配置管理中心 - 管理工具集的全局配置."""

from pydantic import BaseModel, Field


class ToolsConfig(BaseModel):
    """工具集全局配置模型.

    使用Pydantic v2进行数据验证.
    """

    # 是否显示详细日志信息
    verbose: bool = Field(default=False, description="是否显示详细日志信息")
    # 默认输出格式（text, json, table）
    output_format: str = Field(default="text", description="默认输出格式")
    # 是否显示进度条
    show_progress: bool = Field(default=True, description="是否显示进度条")


# 创建默认配置实例
default_config = ToolsConfig()


def get_config() -> ToolsConfig:
    """获取当前配置.

    返回：当前配置对象.
    """
    return default_config
