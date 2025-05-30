# tests/test_file_tool_format.py
"""file_tool 格式化功能测试."""
import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from simple_tools.cli import cli


class TestFileToolFormat:
    """测试 file_tool 的格式化功能."""

    def setup_method(self) -> None:
        """Set up test CLI runner."""
        self.runner = CliRunner()

    def test_list_with_long_option_json(self) -> None:
        """测试带 --long 选项的 JSON 输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = Path(tmpdir, "test.txt")
            test_file.write_text("content")

            result = self.runner.invoke(
                cli, ["list", tmpdir, "--long", "--format", "json"]
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "modified" in data["files"][0]

    def test_list_empty_directory_json(self) -> None:
        """测试空目录的 JSON 输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.runner.invoke(cli, ["list", tmpdir, "--format", "json"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total"] == 0
            assert data["files"] == []

    def test_list_with_hidden_files_csv(self) -> None:
        """测试包含隐藏文件的 CSV 输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建隐藏文件
            Path(tmpdir, ".hidden").write_text("hidden")
            Path(tmpdir, "visible.txt").write_text("visible")

            # 不带 --all，不应该显示隐藏文件
            result = self.runner.invoke(cli, ["list", tmpdir, "--format", "csv"])
            assert ".hidden" not in result.output

            # 带 --all，应该显示隐藏文件
            result = self.runner.invoke(
                cli, ["list", tmpdir, "--all", "--format", "csv"]
            )
            assert ".hidden" in result.output
