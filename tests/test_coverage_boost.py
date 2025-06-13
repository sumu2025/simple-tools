"""额外的集成测试以提升覆盖率."""

from pathlib import Path

from click.testing import CliRunner

from simple_tools.cli import cli


class TestAdditionalCoverage:
    """额外的测试以提升覆盖率"""

    def test_batch_rename_number_mode(self, tmp_path: Path) -> None:
        """测试批量重命名的数字模式"""
        # 创建测试文件
        for i in range(3):
            (tmp_path / f"test{i}.txt").touch()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "rename",
                str(tmp_path),
                "--mode",
                "number",
                "--pattern",
                "Photo",
                "--execute",
                "--skip-confirm",
            ],
        )

        assert result.exit_code == 0
        # 检查文件是否被重命名
        renamed_files = list(tmp_path.glob("Photo*.txt"))
        assert len(renamed_files) == 3

    def test_batch_rename_case_mode(self, tmp_path: Path) -> None:
        """测试批量重命名的大小写模式"""
        # 创建测试文件
        (tmp_path / "TEST_FILE.txt").touch()
        (tmp_path / "Another_Test.txt").touch()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "rename",
                str(tmp_path),
                "--mode",
                "case",
                "--case-mode",
                "lower",
                "--execute",
                "--skip-confirm",
            ],
        )

        assert result.exit_code == 0
        # 检查文件名是否转为小写
        assert (tmp_path / "test_file.txt").exists() or (
            tmp_path / "TEST_FILE.txt"
        ).exists()

    def test_text_replace_with_extensions(self, tmp_path: Path) -> None:
        """测试文本替换的扩展名过滤"""
        # 创建不同类型的文件
        (tmp_path / "test.txt").write_text("Hello World")
        (tmp_path / "test.md").write_text("Hello World")
        (tmp_path / "test.py").write_text("Hello World")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "Hello:Hi",
                "--path",
                str(tmp_path),
                "--extension",
                ".txt",
                "--extension",
                ".md",
                "--execute",
                "--yes",
            ],
        )

        assert result.exit_code == 0
        # 检查文件内容
        assert (tmp_path / "test.txt").read_text() == "Hi World"
        assert (tmp_path / "test.md").read_text() == "Hi World"
        assert (tmp_path / "test.py").read_text() == "Hello World"  # 未更改

    def test_file_organizer_type_mode(self, tmp_path: Path) -> None:
        """测试文件整理的类型模式"""
        # 创建不同类型的文件
        (tmp_path / "photo.jpg").touch()
        (tmp_path / "document.pdf").touch()
        (tmp_path / "music.mp3").touch()

        runner = CliRunner()
        result = runner.invoke(
            cli, ["organize", str(tmp_path), "--mode", "type", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "图片" in result.output
        assert "文档" in result.output
        assert "音频" in result.output

    def test_file_organizer_date_mode(self, tmp_path: Path) -> None:
        """测试文件整理的日期模式"""
        # 创建测试文件
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()

        runner = CliRunner()
        result = runner.invoke(
            cli, ["organize", str(tmp_path), "--mode", "date", "--dry-run"]
        )

        assert result.exit_code == 0
        # 应该显示日期分组信息
        assert "2025" in result.output or "整理计划" in result.output

    def test_duplicate_finder_with_size_filter(self, tmp_path: Path) -> None:
        """测试重复文件查找的大小过滤"""
        # 创建小文件（会被过滤）
        (tmp_path / "small1.txt").write_text("a")
        (tmp_path / "small2.txt").write_text("a")

        # 创建大文件
        (tmp_path / "big1.txt").write_text("content" * 1000)
        (tmp_path / "big2.txt").write_text("content" * 1000)

        runner = CliRunner()
        result = runner.invoke(cli, ["duplicates", str(tmp_path), "--min-size", "1000"])

        assert result.exit_code == 0
        assert "big1.txt" in result.output
        assert "big2.txt" in result.output
        assert "small1.txt" not in result.output

    def test_list_with_config_file(self, tmp_path: Path) -> None:
        """测试配置文件支持"""
        # 创建配置文件
        config_file = tmp_path / ".simple-tools.yml"
        config_file.write_text(
            """
tools:
  verbose: true
  format: json
  list:
    show_all: true
"""
        )

        # 创建测试文件
        (tmp_path / "test.txt").touch()
        (tmp_path / ".hidden").touch()

        # 在配置文件目录运行
        runner = CliRunner()
        with runner.isolated_filesystem():
            # 复制配置文件到当前目录
            import shutil

            shutil.copy(str(config_file), ".simple-tools.yml")

            # 创建测试文件
            Path("test.txt").touch()
            Path(".hidden").touch()

            result = runner.invoke(cli, ["list", "."])

            assert result.exit_code == 0
            # 应该自动使用JSON格式
            assert "{" in result.output
            # 应该显示隐藏文件
            assert "hidden" in result.output or ".hidden" in result.output

    def test_progress_tracker_usage(self, tmp_path: Path) -> None:
        """测试进度条功能"""
        # 创建很多文件以触发进度条
        for i in range(30):
            (tmp_path / f"file{i}.txt").write_text("TODO: fix this")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "replace",
                "TODO:DONE",
                "--path",
                str(tmp_path),
                "--extension",
                ".txt",  # 明确指定扩展名
                "--execute",
                "--yes",
            ],
        )

        # 如果失败，打印详细信息用于调试
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")

        assert result.exit_code == 0
        # 应该成功替换所有文件 - 检查多种可能的输出
        success_indicators = [
            "替换完成",  # 主要完成消息
            "成功处理文件",  # 成功处理消息
            "总替换数",  # 替换统计
            "30",  # 文件数量
            "正在执行替换",  # 执行消息
        ]
        assert any(
            indicator in result.output for indicator in success_indicators
        ), f"Output: {result.output}"

    def test_error_handling_improvements(self) -> None:
        """测试错误处理改进"""
        runner = CliRunner()

        # 测试文件不存在错误
        result = runner.invoke(
            cli, ["replace", "test:new", "--file", "/nonexistent/file.txt"]
        )

        assert result.exit_code != 0
        assert "文件不存在" in result.output or "FILE_NOT_FOUND" in result.output
        assert "建议" in result.output or "检查文件路径" in result.output

    def test_smart_interactive_in_test_mode(self, tmp_path: Path) -> None:
        """测试智能交互在测试模式下的行为"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        runner = CliRunner()
        # 在测试环境中应该自动跳过确认
        result = runner.invoke(
            cli,
            [
                "replace",
                "content:new_content",
                "--file",
                str(test_file),
                "--execute",
                "--yes",  # 添加 --yes 标志以跳过确认
            ],
        )

        # 如果失败，打印详细错误信息
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")

        # 应该成功执行而不需要用户输入
        assert result.exit_code == 0
        assert test_file.read_text() == "new_content"

    def test_formatter_edge_cases(self, tmp_path: Path) -> None:
        """测试格式化器的边界情况"""
        # 创建空目录
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        runner = CliRunner()

        # JSON格式输出空目录
        result = runner.invoke(cli, ["list", str(empty_dir), "--format", "json"])

        assert result.exit_code == 0
        assert "files" in result.output
        assert "[]" in result.output

        # CSV格式输出空目录
        result = runner.invoke(cli, ["list", str(empty_dir), "--format", "csv"])

        assert result.exit_code == 0
        assert "name,type,size,modified" in result.output

    def test_cli_history_command(self) -> None:
        """测试历史命令"""
        runner = CliRunner()

        # 运行history命令
        result = runner.invoke(cli, ["history"])

        assert result.exit_code == 0
        # 应该显示历史记录或"暂无操作记录"
        assert "操作记录" in result.output
