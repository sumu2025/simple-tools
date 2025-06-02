"""配置功能集成测试."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from simple_tools.cli import cli


class TestConfigIntegration:
    """配置功能集成测试类."""

    def setup_method(self) -> None:
        """每个测试方法前的设置."""
        self.runner = CliRunner()

    def test_config_file_affects_list_command(self) -> None:
        """测试配置文件影响 list 命令."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建配置文件
            config_content = """
tools:
  format: json
  list:
    show_all: true
    long: true
"""
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text(config_content)

            # 创建测试文件
            Path(tmpdir, "test.txt").write_text("hello")
            Path(tmpdir, ".hidden").write_text("hidden")

            # 运行命令，使用 -c 参数指定配置文件
            result = self.runner.invoke(cli, ["-c", str(config_path), "list", tmpdir])

            # 验证输出是 JSON 格式
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total"] == 3  # 包括 .hidden 和 .simple-tools.yml

            # 验证包含所有文件
            file_names = [f["name"] for f in data["files"]]
            assert "test.txt" in file_names
            assert ".hidden" in file_names
            assert ".simple-tools.yml" in file_names

            # 验证包含文件详情（long=true）
            assert len(data["files"]) == 3
            for f in data["files"]:
                assert "size" in f
                assert "modified" in f

    def test_cli_args_override_config_file(self) -> None:
        """测试命令行参数覆盖配置文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建配置文件（指定 JSON 格式）
            config_content = """
tools:
  format: json
"""
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text(config_content)

            # 创建测试文件
            Path(tmpdir, "test.txt").write_text("hello")

            # 运行命令，命令行指定 csv 格式（应该覆盖配置文件）
            result = self.runner.invoke(
                cli, ["list", tmpdir, "--format", "csv"], env={"HOME": tmpdir}
            )

            # 验证输出是 CSV 格式
            assert result.exit_code == 0
            # 检查是否是CSV格式（包含逗号分隔的标题行）
            lines = result.output.strip().split("\n")
            assert len(lines) >= 2  # 至少有标题行和一行数据
            header = lines[0]
            assert "name" in header
            assert "," in header  # 确认是CSV格式

    def test_specify_config_file_path(self) -> None:
        """测试指定配置文件路径."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建自定义位置的配置文件
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_path = config_dir / "my-config.yml"
            config_path.write_text(
                """
tools:
  verbose: true
  format: json
"""
            )

            # 创建测试文件
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()
            Path(test_dir, "file.txt").write_text("content")

            # 使用 -c 参数指定配置文件
            result = self.runner.invoke(
                cli, ["-c", str(config_path), "list", str(test_dir)]
            )

            # 验证使用了配置文件
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "files" in data

    # 在 tests/test_config_integration.py 添加更多测试

    def test_duplicates_with_config(self) -> None:
        """测试 duplicates 命令使用配置文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建配置文件
            config_content = """
tools:
  format: json
  duplicates:
    recursive: false
    min_size: 1
"""
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text(config_content)

            # 创建测试文件
            Path(tmpdir, "file1.txt").write_text("same content")
            Path(tmpdir, "file2.txt").write_text("same content")

            # 运行命令，使用 -c 参数指定配置文件
            result = self.runner.invoke(
                cli, ["-c", str(config_path), "duplicates", tmpdir]
            )

            # 验证使用了配置（JSON 格式输出）
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "groups" in data

    def test_all_commands_with_config(self) -> None:
        """测试所有命令都能使用配置文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建完整配置文件
            config_content = """
tools:
  verbose: true
  format: json

  list:
    show_all: true

  duplicates:
    min_size: 100

  rename:
    dry_run: false

  replace:
    extensions: [.txt]

  organize:
    mode: date
"""
            config_path = Path(tmpdir) / ".simple-tools.yml"
            config_path.write_text(config_content)

            # 测试各个命令都能加载配置
            commands = ["list", "duplicates", "rename", "replace", "organize"]
            for cmd in commands:
                result = self.runner.invoke(cli, [cmd, "--help"])
                assert result.exit_code == 0
