"""配置文件加载工具模块."""

import os
from pathlib import Path
from re import Match
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ListConfig(BaseModel):
    """list 命令配置."""

    show_all: bool = Field(False, description="显示隐藏文件")
    long: bool = Field(False, description="显示详细信息")


class DuplicatesConfig(BaseModel):
    """duplicates 命令配置."""

    recursive: bool = Field(True, description="递归扫描")
    min_size: int = Field(1, description="最小文件大小")
    extensions: Optional[list[str]] = Field(None, description="文件扩展名")


class RenameConfig(BaseModel):
    """rename 命令配置."""

    dry_run: bool = Field(True, description="预览模式")
    skip_confirm: bool = Field(False, description="跳过确认")


class ReplaceConfig(BaseModel):
    """replace 命令配置."""

    extensions: list[str] = Field(default_factory=list, description="文件扩展名")
    dry_run: bool = Field(True, description="预览模式")


class OrganizeConfig(BaseModel):
    """organize 命令配置."""

    mode: str = Field("type", description="整理模式")
    recursive: bool = Field(False, description="递归处理")
    dry_run: bool = Field(True, description="预览模式")


class ToolConfig(BaseModel):
    """工具配置模型."""

    verbose: bool = Field(False, description="详细输出")
    format: str = Field("plain", description="输出格式")

    # 各工具配置
    list: ListConfig = Field(default_factory=ListConfig)
    duplicates: DuplicatesConfig = Field(default_factory=DuplicatesConfig)
    rename: RenameConfig = Field(default_factory=RenameConfig)
    replace: ReplaceConfig = Field(default_factory=ReplaceConfig)
    organize: OrganizeConfig = Field(default_factory=OrganizeConfig)

    def __init__(self, **data: Any) -> None:
        """初始化工具配置对象，处理嵌套的配置字典.

        Args:
            data: 配置数据字典

        """
        # 处理嵌套的字典配置
        if "list" in data and isinstance(data["list"], dict):
            data["list"] = ListConfig(**data["list"])
        if "duplicates" in data and isinstance(data["duplicates"], dict):
            data["duplicates"] = DuplicatesConfig(**data["duplicates"])
        if "rename" in data and isinstance(data["rename"], dict):
            data["rename"] = RenameConfig(**data["rename"])
        if "replace" in data and isinstance(data["replace"], dict):
            data["replace"] = ReplaceConfig(**data["replace"])
        if "organize" in data and isinstance(data["organize"], dict):
            data["organize"] = OrganizeConfig(**data["organize"])

        super().__init__(**data)


def find_config_file(start_path: str = ".") -> Optional[Path]:
    """查找配置文件.

    查找顺序：
    1. 当前目录的 .simple-tools.yml 或 .simple-tools.yaml
    2. 用户主目录的配置文件

    Args:
        start_path: 开始查找的路径

    Returns:
        找到的配置文件路径，如果没找到返回 None

    """
    config_names = [".simple-tools.yml", ".simple-tools.yaml"]

    # 先在指定目录查找
    start_dir = Path(start_path).resolve()
    for name in config_names:
        config_path = start_dir / name
        if config_path.exists():
            return config_path

    # 在用户主目录查找
    home_dir = Path.home()
    for name in config_names:
        config_path = home_dir / name
        if config_path.exists():
            return config_path

    return None


def merge_configs(file_config: ToolConfig, cli_args: dict[str, Any]) -> ToolConfig:
    """合并配置（命令行参数优先）.

    Args:
        file_config: 从文件加载的配置
        cli_args: 命令行参数

    Returns:
        合并后的配置

    """
    # 将文件配置转为字典
    config_dict = file_config.model_dump()

    # 递归合并配置
    def merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    # 合并配置
    merged_dict = merge_dict(config_dict, cli_args)

    # 返回新的配置对象
    return ToolConfig(**merged_dict)


class ConfigLoader:
    """配置文件加载器."""

    def __init__(self) -> None:
        """初始化配置加载器，创建配置缓存."""
        self.config_cache: Optional[ToolConfig] = None

    def load_config(self, config_path: str) -> ToolConfig:
        """加载配置文件.

        Args:
            config_path: 配置文件路径

        Returns:
            配置对象

        """
        path = Path(config_path)
        if not path.exists():
            return ToolConfig()

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

                # 替换环境变量
                content = self._expand_env_vars(content)

                # 解析 YAML
                data = yaml.safe_load(content) or {}

                # 获取 tools 配置部分
                tools_config = data.get("tools", {})

                # 创建配置对象
                return ToolConfig(**tools_config)

        except yaml.YAMLError:
            raise
        except Exception:
            return ToolConfig()

    def load_from_directory(self, directory: str = ".") -> ToolConfig:
        """从目录加载配置.

        Args:
            directory: 目录路径

        Returns:
            配置对象

        """
        config_file = find_config_file(directory)
        if config_file:
            return self.load_config(str(config_file))
        return ToolConfig()

    def _expand_env_vars(self, content: str) -> str:
        """展开配置中的环境变量.

        支持 ${VAR_NAME} 格式

        Args:
            content: 配置文件内容

        Returns:
            替换后的内容

        """
        import re

        def replace_env_var(match: Match[str]) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        # 替换 ${VAR_NAME} 格式的环境变量
        pattern = r"\$\{([^}]+)\}"
        return re.sub(pattern, replace_env_var, content)
