"""测试辅助工具模块."""

from typing import Any, Optional

from simple_tools.utils.config_loader import (
    DuplicatesConfig,
    ListConfig,
    OrganizeConfig,
    RenameConfig,
    ReplaceConfig,
    ToolConfig,
)


def create_test_config(
    verbose: bool = False,
    format: str = "plain",
    list_config: Optional[dict[str, Any]] = None,
    duplicates_config: Optional[dict[str, Any]] = None,
    rename_config: Optional[dict[str, Any]] = None,
    replace_config: Optional[dict[str, Any]] = None,
    organize_config: Optional[dict[str, Any]] = None,
) -> ToolConfig:
    """创建测试用的配置对象.

    Args:
        verbose: 是否启用详细输出
        format: 输出格式
        list_config: list命令配置
        duplicates_config: duplicates命令配置
        rename_config: rename命令配置
        replace_config: replace命令配置
        organize_config: organize命令配置

    Returns:
        完整的ToolConfig对象

    """
    # 创建各命令的配置
    list_cfg = ListConfig(**(list_config or {}))
    duplicates_cfg = DuplicatesConfig(**(duplicates_config or {}))
    rename_cfg = RenameConfig(**(rename_config or {}))
    replace_cfg = ReplaceConfig(**(replace_config or {}))
    organize_cfg = OrganizeConfig(**(organize_config or {}))

    # 创建完整的配置对象
    return ToolConfig(
        verbose=verbose,
        format=format,
        list=list_cfg,
        duplicates=duplicates_cfg,
        rename=rename_cfg,
        replace=replace_cfg,
        organize=organize_cfg,
    )


def create_mock_context(config: Optional[ToolConfig] = None) -> dict[str, Any]:
    """创建测试用的Click上下文.

    Args:
        config: 配置对象，如果为None则使用默认配置

    Returns:
        包含配置的上下文字典

    """
    if config is None:
        config = create_test_config()

    return {"config": config}
