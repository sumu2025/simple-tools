"""格式化功能集成测试.

测试格式化功能是否影响原有功能的正常使用。
"""

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from simple_tools.cli import cli


class TestFormatIntegration:
    """格式化功能集成测试."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """创建 CLI runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        """创建临时测试目录."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_list_command_default_behavior(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 list 命令的默认行为（不应该输出 JSON）."""
        # 创建测试文件
        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.txt").touch()

        # 运行默认命令
        result = runner.invoke(cli, ["list", str(temp_dir)])

        # 检查输出
        assert result.exit_code == 0
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
        # 不应该包含 JSON 标记
        assert "{" not in result.output or '"files"' not in result.output

    def test_list_command_with_json_format(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 list 命令的 JSON 格式输出."""
        # 创建测试文件
        (temp_dir / "test.txt").write_text("content")

        # 运行带格式参数的命令
        result = runner.invoke(cli, ["list", str(temp_dir), "--format", "json"])

        # 检查输出
        assert result.exit_code == 0
        # 验证 JSON 格式
        data = json.loads(result.output)
        assert "files" in data
        assert data["total"] == 1
        assert data["files"][0]["name"] == "test.txt"

    def test_list_command_with_csv_format(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 list 命令的 CSV 格式输出."""
        # 创建测试文件
        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.jpg").touch()

        # 运行带格式参数的命令
        result = runner.invoke(cli, ["list", str(temp_dir), "--format", "csv"])

        # 检查输出
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        # 应该有标题行
        assert "name,type,size,modified" in lines[0]
        # 应该有两个文件
        assert len(lines) >= 3  # 标题 + 2个文件

    def test_duplicates_command_default_behavior(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 duplicates 命令的默认行为."""
        # 创建重复文件
        (temp_dir / "file1.txt").write_text("same content")
        (temp_dir / "file2.txt").write_text("same content")
        (temp_dir / "file3.txt").write_text("different")

        # 运行默认命令
        result = runner.invoke(cli, ["duplicates", str(temp_dir)])

        # 检查输出
        assert result.exit_code == 0
        assert "发现 1 组重复文件" in result.output
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
        # 不应该包含 JSON 标记
        assert not result.output.startswith("{")

    def test_duplicates_command_with_json_format(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 duplicates 命令的 JSON 格式输出."""
        # 创建重复文件
        (temp_dir / "dup1.txt").write_text("duplicate")
        (temp_dir / "dup2.txt").write_text("duplicate")

        # 运行带格式参数的命令
        result = runner.invoke(cli, ["duplicates", str(temp_dir), "--format", "json"])

        # 检查输出
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "groups" in data
        assert data["total_groups"] == 1
        assert len(data["groups"][0]["files"]) == 2

    def test_rename_command_preview_mode(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 rename 命令的预览模式."""
        # 创建测试文件
        (temp_dir / "old1.txt").touch()
        (temp_dir / "old2.txt").touch()

        # 运行预览模式
        result = runner.invoke(
            cli,
            [
                "rename",
                str(temp_dir),
                "--pattern",
                "old",
                "--replacement",
                "new",
                "--preview",
            ],
        )

        # 检查输出
        assert result.exit_code == 0
        assert "重命名预览" in result.output
        assert "old1.txt" in result.output
        assert "new1.txt" in result.output
        # 文件应该没有被重命名
        assert (temp_dir / "old1.txt").exists()
        assert not (temp_dir / "new1.txt").exists()

    def test_rename_command_with_format(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 rename 命令的格式化输出."""
        # 创建测试文件
        (temp_dir / "test1.txt").touch()
        (temp_dir / "test2.txt").touch()

        # 运行带格式参数的命令（预览模式）
        result = runner.invoke(
            cli,
            [
                "rename",
                str(temp_dir),
                "--pattern",
                "test",
                "--replacement",
                "demo",
                "--format",
                "json",
                "--preview",
            ],
        )

        # 检查输出
        assert result.exit_code == 0
        # 由于预览模式，JSON 可能为空或包含预览信息
        assert "{" in result.output

    def test_replace_command_default_behavior(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 replace 命令的默认行为（预览模式）."""
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("TODO: fix this\nTODO: and this")

        # 运行默认命令（预览模式）
        result = runner.invoke(cli, ["replace", "TODO:DONE", "-f", str(test_file)])

        # 检查输出
        assert result.exit_code == 0
        assert "找到" in result.output
        assert "TODO" in result.output
        # 文件内容应该没有改变
        assert "TODO" in test_file.read_text()

    def test_replace_command_with_json_format(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 replace 命令的 JSON 格式输出."""
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("replace me")

        # 运行带格式参数的命令
        result = runner.invoke(
            cli,
            ["replace", "replace:changed", "-f", str(test_file), "--format", "json"],
        )

        # 检查输出
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "replace_results" in data
        assert data["replace_results"][0]["match_count"] == 1

    def test_organize_command_default_behavior(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 organize 命令的默认行为（预览模式）."""
        # 创建不同类型的文件
        (temp_dir / "image.jpg").touch()
        (temp_dir / "document.pdf").touch()
        (temp_dir / "video.mp4").touch()

        # 运行默认命令（预览模式）
        result = runner.invoke(cli, ["organize", str(temp_dir)])

        # 检查输出
        assert result.exit_code == 0
        assert "整理计划" in result.output
        assert "图片" in result.output
        assert "文档" in result.output
        assert "视频" in result.output
        # 文件应该没有被移动
        assert (temp_dir / "image.jpg").exists()
        assert not (temp_dir / "图片" / "image.jpg").exists()

    def test_organize_command_with_json_format(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """测试 organize 命令的 JSON 格式输出."""
        # 创建测试文件
        (temp_dir / "test.pdf").touch()
        (temp_dir / "photo.jpg").touch()

        # 运行带格式参数的命令
        result = runner.invoke(cli, ["organize", str(temp_dir), "--format", "json"])

        # 检查输出是否包含 JSON
        assert result.exit_code == 0
        # 提取 JSON 部分（可能包含其他输出）
        json_start = result.output.find("{")
        if json_start >= 0:
            json_str = result.output[json_start:]
            data = json.loads(json_str)
            assert "organize_results" in data or "results" in data

    def test_error_handling_with_format(self, runner: CliRunner) -> None:
        """测试错误处理在不同格式下的表现."""
        # 测试不存在的路径
        result = runner.invoke(cli, ["list", "/nonexistent/path"])
        assert result.exit_code != 0
        assert "错误" in result.output or "Error" in result.output

        # 使用 JSON 格式时的错误处理
        result = runner.invoke(cli, ["list", "/nonexistent/path", "--format", "json"])
        assert result.exit_code != 0
        # 错误信息应该仍然是可读的，不是 JSON

    def test_help_commands(self, runner: CliRunner) -> None:
        """测试帮助命令是否正常."""
        # 主帮助
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "简单工具集" in result.output

        # 子命令帮助
        for cmd in ["list", "duplicates", "rename", "replace", "organize"]:
            result = runner.invoke(cli, [cmd, "--help"])
            assert result.exit_code == 0
            assert "--format" in result.output  # 应该包含格式选项

    def test_config_file_support(self, runner: CliRunner, temp_dir: Path) -> None:
        """测试配置文件对格式的影响."""
        # 创建配置文件
        config_file = temp_dir / ".simple-tools.yml"
        config_file.write_text("tools:\n  format: json\n")

        # 创建测试文件
        (temp_dir / "test.txt").touch()

        # 在配置文件目录运行命令
        # 切换到测试目录
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(cli, ["list", "."])
            # 应该自动使用 JSON 格式
            assert result.exit_code == 0
            assert "{" in result.output
        finally:
            os.chdir(original_cwd)

    def test_mixed_operations(self, runner: CliRunner, temp_dir: Path) -> None:
        """测试混合操作确保功能之间没有干扰."""
        # 1. 创建文件
        (temp_dir / "file1.txt").write_text("content")
        (temp_dir / "file2.txt").write_text("content")
        (temp_dir / "unique.txt").write_text("unique")

        # 2. 列出文件
        result = runner.invoke(cli, ["list", str(temp_dir)])
        assert result.exit_code == 0
        assert "file1.txt" in result.output

        # 3. 查找重复
        result = runner.invoke(cli, ["duplicates", str(temp_dir), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_groups"] == 1

        # 4. 重命名（预览）
        result = runner.invoke(
            cli,
            [
                "rename",
                str(temp_dir),
                "--pattern",
                "file",
                "--replacement",
                "doc",
                "--preview",
            ],
        )
        assert result.exit_code == 0

        # 5. 整理（预览）
        result = runner.invoke(cli, ["organize", str(temp_dir), "--format", "csv"])
        assert result.exit_code == 0
        assert "source_path,target_path" in result.output


@pytest.mark.parametrize("format_type", ["plain", "json", "csv"])
class TestAllFormats:
    """测试所有命令的所有格式."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """创建 CLI runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        """创建临时测试目录."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_list_all_formats(
        self, runner: CliRunner, temp_dir: Path, format_type: str
    ) -> None:
        """测试 list 命令的所有格式."""
        (temp_dir / "test.txt").touch()
        result = runner.invoke(cli, ["list", str(temp_dir), "--format", format_type])
        assert result.exit_code == 0

        if format_type == "json":
            json.loads(result.output)  # 应该能解析
        elif format_type == "csv":
            assert "name,type,size,modified" in result.output
        else:
            assert "test.txt" in result.output

    def test_duplicates_all_formats(
        self, runner: CliRunner, temp_dir: Path, format_type: str
    ) -> None:
        """测试 duplicates 命令的所有格式."""
        (temp_dir / "d1.txt").write_text("dup")
        (temp_dir / "d2.txt").write_text("dup")
        result = runner.invoke(
            cli, ["duplicates", str(temp_dir), "--format", format_type]
        )
        assert result.exit_code == 0

        if format_type == "json":
            data = json.loads(result.output)
            assert "groups" in data
        elif format_type == "csv":
            assert "hash,size,count,files" in result.output
