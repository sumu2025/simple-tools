# tests/test_text_replace.py
"""文本替换工具测试."""
import tempfile
from pathlib import Path

from click.testing import CliRunner

from simple_tools.cli import cli


class TestTextReplace:
    """文本替换工具测试类."""

    def setup_method(self) -> None:
        """初始化测试运行器."""
        self.runner = CliRunner()

    def test_single_file_replace(self) -> None:
        """测试单文件替换."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = Path(tmpdir, "test.txt")
            test_file.write_text("Hello World\nHello Python")

            # 执行替换
            result = self.runner.invoke(
                cli, ["replace", "Hello:Hi", "-f", str(test_file), "--execute", "--yes"]
            )

            assert result.exit_code == 0
            content = test_file.read_text()
            assert "Hi World" in content
            assert "Hi Python" in content

    def test_directory_replace(self) -> None:
        """测试目录批量替换."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建多个测试文件
            Path(tmpdir, "file1.txt").write_text("old text")
            Path(tmpdir, "file2.txt").write_text("old text here")
            Path(tmpdir, "file3.md").write_text("old content")

            # 执行替换（只处理txt文件）
            result = self.runner.invoke(
                cli,
                [
                    "replace",
                    "old:new",
                    "-p",
                    tmpdir,
                    "-e",
                    ".txt",
                    "--execute",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert Path(tmpdir, "file1.txt").read_text() == "new text"
            assert Path(tmpdir, "file2.txt").read_text() == "new text here"
            assert Path(tmpdir, "file3.md").read_text() == "old content"  # 未改变

    def test_dry_run_mode(self) -> None:
        """测试预览模式."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir, "test.txt")
            test_file.write_text("foo bar foo")

            # 默认是预览模式
            result = self.runner.invoke(
                cli, ["replace", "foo:baz", "-f", str(test_file)]
            )

            assert result.exit_code == 0
            assert "预览" in result.output or "preview" in result.output.lower()
            # 文件内容应该未改变
            assert test_file.read_text() == "foo bar foo"

    def test_empty_replacement(self) -> None:
        """测试替换为空字符串."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir, "test.txt")
            test_file.write_text("remove this word")

            result = self.runner.invoke(
                cli, ["replace", "this:", "-f", str(test_file), "--execute", "--yes"]
            )

            assert result.exit_code == 0
            assert test_file.read_text() == "remove  word"

    def test_no_matches_found(self) -> None:
        """测试没有找到匹配内容."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir, "test.txt")
            test_file.write_text("hello world")

            result = self.runner.invoke(
                cli,
                [
                    "replace",
                    "notfound:replaced",
                    "-f",
                    str(test_file),
                    "--execute",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert test_file.read_text() == "hello world"  # 未改变
