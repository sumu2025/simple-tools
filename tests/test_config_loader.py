# tests/test_config_loader.py
"""配置文件加载功能的测试."""
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from simple_tools.utils.config_loader import (
    ConfigLoader,
    ToolConfig,
    find_config_file,
    merge_configs,
)


class TestConfigLoader:
    """配置文件加载测试类."""

    def test_find_config_file_in_current_dir(self) -> None:
        """测试在当前目录查找配置文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建配置文件
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text("tools:\n  verbose: true")

            # 查找配置文件
            found = find_config_file(tmpdir)
            # 使用 resolve() 解决符号链接问题
            assert found is not None and found.resolve() == config_path.resolve()

    def test_find_config_file_in_home_dir(self, monkeypatch: Any) -> None:
        """测试在用户目录查找配置文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 模拟用户目录
            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()
            config_path = home_dir / ".simple-tools.yml"
            config_path.write_text("tools:\n  verbose: true")

            # 修改 HOME 环境变量
            monkeypatch.setenv("HOME", str(home_dir))

            # 在没有配置文件的目录下查找
            work_dir = Path(tmpdir) / "work"
            work_dir.mkdir()

            found = find_config_file(str(work_dir))
            assert found == config_path

    def test_find_config_file_not_found(self) -> None:
        """测试找不到配置文件的情况."""
        with tempfile.TemporaryDirectory() as tmpdir:
            found = find_config_file(tmpdir)
            assert found is None

    def test_load_valid_config(self) -> None:
        """测试加载有效的配置文件."""
        config_content = """
tools:
  verbose: true
  format: json

  list:
    show_all: true
    long: true

  duplicates:
    recursive: true
    min_size: 1048576

  rename:
    dry_run: true

  replace:
    extensions: [.txt, .md, .rst]

  organize:
    mode: type
    recursive: false
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text(config_content)

            loader = ConfigLoader()
            config = loader.load_config(str(config_path))

            assert config.verbose is True
            assert config.format == "json"
            assert config.list.show_all is True
            assert config.list.long is True
            assert config.duplicates.recursive is True
            assert config.duplicates.min_size == 1048576

    def test_load_empty_config(self) -> None:
        """测试加载空配置文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text("")

            loader = ConfigLoader()
            config = loader.load_config(str(config_path))

            # 应该返回默认配置
            assert config.verbose is False
            assert config.format == "plain"

    def test_load_partial_config(self) -> None:
        """测试加载部分配置."""
        config_content = """
tools:
  list:
    show_all: true
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text(config_content)

            loader = ConfigLoader()
            config = loader.load_config(str(config_path))

            # 指定的值应该被设置
            assert config.list.show_all is True
            # 未指定的值应该使用默认值
            assert config.list.long is False
            assert config.verbose is False

    def test_merge_configs(self) -> None:
        """测试配置合并（命令行参数优先）."""
        # 文件配置
        file_config = ToolConfig(
            verbose=True, format="json", list={"show_all": True, "long": True}
        )

        # 命令行参数（优先级更高）
        cli_args: dict[str, Any] = {
            "verbose": False,  # 覆盖文件配置
            "format": "csv",  # 覆盖文件配置
            "list": {"show_all": False},  # 部分覆盖
        }

        merged = merge_configs(file_config, cli_args)
        # 命令行参数应该优先
        assert merged.verbose is False
        assert merged.format == "csv"
        # 使用属性访问而不是下标
        assert merged.list.show_all is False
        # 文件配置中的其他值应该保留
        assert merged.list.long is True

    def test_invalid_yaml_file(self) -> None:
        """测试无效的YAML文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text("invalid: yaml: content:")

            loader = ConfigLoader()
            with pytest.raises(yaml.YAMLError):
                loader.load_config(str(config_path))

    def test_config_file_with_env_vars(self, monkeypatch: Any) -> None:
        """测试配置文件中的环境变量替换."""
        monkeypatch.setenv("SIMPLE_TOOLS_MIN_SIZE", "2048")

        config_content = """
tools:
  duplicates:
    min_size: ${SIMPLE_TOOLS_MIN_SIZE}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text(config_content)

            loader = ConfigLoader()
            config = loader.load_config(str(config_path))

            assert config.duplicates.min_size == 2048

    def test_config_precedence(self) -> None:
        """测试配置优先级：命令行 > 当前目录 > 用户目录."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 用户目录配置
            home_config = Path(tmpdir) / "home" / ".simple-tools.yml"
            home_config.parent.mkdir()
            home_config.write_text("tools:\n  verbose: true\n  format: json")

            # 当前目录配置
            current_config = Path(tmpdir) / "current" / ".simple-tools.yml"
            current_config.parent.mkdir()
            current_config.write_text("tools:\n  verbose: false\n  format: csv")

            loader = ConfigLoader()

            # 加载当前目录配置（应该覆盖用户目录）
            config = loader.load_from_directory(str(current_config.parent))
            assert config.verbose is False
            assert config.format == "csv"
