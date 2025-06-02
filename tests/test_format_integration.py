# tests/test_format_integration.py
"""格式化功能集成测试."""
import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from simple_tools.cli import cli


class TestFormatIntegration:
    """格式化功能集成测试类."""

    def setup_method(self) -> None:
        """每个测试方法前的设置."""
        self.runner = CliRunner()

    def test_list_command_with_json_format(self) -> None:
        """测试 list 命令的 JSON 格式输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "test.txt").write_text("hello")
            Path(tmpdir, "test.py").write_text("print('hello')")

            # 运行命令
            result = self.runner.invoke(cli, ["list", tmpdir, "--format", "json"])

            # 验证输出
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total"] == 2
            assert len(data["files"]) == 2
            assert any(f["name"] == "test.txt" for f in data["files"])

    def test_list_command_with_csv_format(self) -> None:
        """测试 list 命令的 CSV 格式输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "test.txt").write_text("hello")

            # 运行命令
            result = self.runner.invoke(cli, ["list", tmpdir, "--format", "csv"])

            # 验证输出
            assert result.exit_code == 0
            assert "name,type,size,modified" in result.output
            assert "test.txt" in result.output

    def test_list_command_default_format(self) -> None:
        """测试 list 命令的默认格式（向后兼容）."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "test.txt").write_text("hello")

            # 运行命令（不指定格式）
            result = self.runner.invoke(cli, ["list", tmpdir])

            # 验证输出（应该是原来的格式）
            assert result.exit_code == 0
            assert "[文件]" in result.output
            assert "test.txt" in result.output
            assert "总计: 1 个项目" in result.output

    # 引入format
    def test_duplicates_command_with_json_format(self) -> None:
        """测试 duplicates 命令的 JSON 格式输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建重复文件
            Path(tmpdir, "file1.txt").write_text("same content")
            Path(tmpdir, "file2.txt").write_text("same content")
            Path(tmpdir, "unique.txt").write_text("different content")

            # 运行命令
            result = self.runner.invoke(cli, ["duplicates", tmpdir, "--format", "json"])
            # 测试临时加入
            print(result.output)
            # 验证输出
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_groups"] == 1
            assert data["total_size_saved"] > 0
            assert len(data["groups"]) == 1
            assert data["groups"][0]["count"] == 2

    def test_duplicates_command_with_csv_format(self) -> None:
        """测试 duplicates 命令的 CSV 格式输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建重复文件
            Path(tmpdir, "file1.txt").write_text("same content")
            Path(tmpdir, "file2.txt").write_text("same content")

            # 运行命令
            result = self.runner.invoke(cli, ["duplicates", tmpdir, "--format", "csv"])

            # 验证输出
            assert result.exit_code == 0
            assert "hash,size,count," in result.output
            assert "file1.txt" in result.output
            assert "file2.txt" in result.output

    def test_duplicates_command_no_duplicates_json(self) -> None:
        """测试没有重复文件时的 JSON 输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建不同内容的文件
            Path(tmpdir, "file1.txt").write_text("content 1")
            Path(tmpdir, "file2.txt").write_text("content 2")

            # 运行命令
            result = self.runner.invoke(cli, ["duplicates", tmpdir, "--format", "json"])

            # 验证输出
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_groups"] == 0
            assert data["groups"] == []
