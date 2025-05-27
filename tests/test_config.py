"""测试 simple_tools.config 模块的全局配置功能."""

from simple_tools.config import ToolsConfig, get_config


def test_get_config_returns_default_config() -> None:
    """测试 get_config 返回默认配置对象及其默认值."""
    config = get_config()
    assert isinstance(config, ToolsConfig)
    # 检查默认值
    assert config.verbose is False
    assert config.output_format == "text"
    assert config.show_progress is True
