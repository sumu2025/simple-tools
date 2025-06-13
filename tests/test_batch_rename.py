"""批量重命名功能测试模块."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from simple_tools.core.batch_rename import BatchRename, rename_cmd


class TestBatchRename:
    """批量重命名功能测试."""

    def test_text_mode_rename(self) -> None:
        """测试文本模式重命名."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_files = [
                temp_path / "test1.txt",
                temp_path / "test2.txt",
                temp_path / "other.txt",
            ]
            for file_path in test_files:
                file_path.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="text",
                pattern="test",
                replacement="renamed",
                interactive=False,
            )
            assert result.total_files == 3
            assert result.successful_renames == 2
            assert result.failed_renames == 0
            assert (temp_path / "renamed1.txt").exists()
            assert (temp_path / "renamed2.txt").exists()
            assert (temp_path / "other.txt").exists()

    def test_number_mode_rename(self) -> None:
        """测试数字模式重命名."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_files = [
                temp_path / "file1.txt",
                temp_path / "file2.txt",
                temp_path / "file3.txt",
            ]
            for file_path in test_files:
                file_path.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="number",
                pattern="doc",
                start_number=10,
                interactive=False,
            )
            assert result.total_files == 3
            assert result.successful_renames == 3
            assert result.failed_renames == 0
            renamed_files = list(temp_path.glob("doc*.txt"))
            assert len(renamed_files) == 3

    def test_preview_mode(self) -> None:
        """测试预览模式."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="text",
                pattern="test",
                replacement="renamed",
                preview_only=True,
            )
            assert result.total_files == 1
            assert result.successful_renames == 0
            assert result.failed_renames == 0
            assert test_file.exists()
            assert not (temp_path / "renamed.txt").exists()

    def test_backup_creation(self) -> None:
        """测试备份创建."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="text",
                pattern="test",
                replacement="renamed",
                create_backup=True,
                interactive=False,
            )
            assert result.total_files == 1
            assert result.successful_renames == 1
            assert result.failed_renames == 0
            assert (temp_path / "renamed.txt").exists()
            # 检查备份文件是否存在（可能有不同的备份命名策略）
            backup_files = list(temp_path.glob("*.bak")) + list(
                temp_path.glob("*backup*")
            )
            assert (
                len(backup_files) >= 1
            ), f"No backup files found in {list(temp_path.iterdir())}"

    def test_recursive_rename(self) -> None:
        """测试递归重命名."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            subdir = temp_path / "subdir"
            subdir.mkdir()
            files = [temp_path / "file1.txt", subdir / "file2.txt"]
            for file_path in files:
                file_path.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="text",
                pattern="file",
                replacement="renamed",
                recursive=True,
                interactive=False,
            )
            assert result.total_files == 2
            assert result.successful_renames == 2
            assert result.failed_renames == 0
            assert (temp_path / "renamed1.txt").exists()
            assert (subdir / "renamed2.txt").exists()

    def test_file_filter(self) -> None:
        """测试文件过滤器."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files = [
                temp_path / "test1.txt",
                temp_path / "test2.py",
                temp_path / "test3.txt",
            ]
            for file_path in files:
                file_path.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="text",
                pattern="test",
                replacement="renamed",
                file_filter="*.txt",
                interactive=False,
            )
            assert result.total_files == 2
            assert result.successful_renames == 2
            assert result.failed_renames == 0
            assert (temp_path / "renamed1.txt").exists()
            assert (temp_path / "renamed3.txt").exists()
            assert (temp_path / "test2.py").exists()

    def test_case_insensitive_mode(self) -> None:
        """测试大小写不敏感模式."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_files = [
                temp_path / "Test1.txt",
                temp_path / "TEST2.txt",
                temp_path / "other.txt",
            ]
            for file_path in test_files:
                file_path.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="text",
                pattern="test",
                replacement="renamed",
                case_insensitive=True,
                interactive=False,
            )
            assert result.total_files == 3
            assert result.successful_renames == 2
            assert result.failed_renames == 0
            assert (temp_path / "renamed1.txt").exists()
            assert (temp_path / "renamed2.txt").exists()
            assert (temp_path / "other.txt").exists()

    def test_regex_mode(self) -> None:
        """测试正则表达式模式."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_files = [
                temp_path / "file001.txt",
                temp_path / "file002.txt",
                temp_path / "other.txt",
            ]
            for file_path in test_files:
                file_path.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="regex",
                pattern=r"file(\d+)",
                replacement=r"document_\1",
                interactive=False,
            )
            assert result.total_files == 3
            assert result.successful_renames == 2
            assert result.failed_renames == 0
            assert (temp_path / "document_001.txt").exists()
            assert (temp_path / "document_002.txt").exists()
            assert (temp_path / "other.txt").exists()

    def test_case_mode(self) -> None:
        """测试大小写转换模式."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_files = [
                temp_path / "DOCUMENT_ALPHA.txt",
                temp_path / "FileB_BETA.txt",
                temp_path / "already_lower_gamma.txt",
            ]
            for file_path in test_files:
                file_path.write_text("test content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path, mode="case", replacement="lower", interactive=False
            )
            assert result.total_files == 3
            assert result.successful_renames == 2
            assert result.skipped_files == 0
            assert result.failed_renames == 0
            assert (temp_path / "document_alpha.txt").exists()
            assert (temp_path / "fileb_beta.txt").exists()
            assert (temp_path / "already_lower_gamma.txt").exists()

    def test_error_handling(self) -> None:
        """测试错误处理."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files = [temp_path / "test1.txt", temp_path / "test2.txt"]
            for file_path in files:
                file_path.write_text("test content")
            conflict_file = temp_path / "renamed1.txt"
            conflict_file.write_text("existing content")
            renamer = BatchRename()
            result = renamer.rename_files(
                temp_path,
                mode="text",
                pattern="test",
                replacement="renamed",
                interactive=False,
            )
            # 扫描到3个文件：test1.txt, test2.txt, renamed1.txt
            assert result.total_files == 3
            # test2.txt -> renamed2.txt
            assert result.successful_renames == 1
            assert result.failed_renames >= 0
            assert result.skipped_files >= 1
            assert (temp_path / "test1.txt").exists()
            assert (temp_path / "renamed1.txt").exists()
            assert (temp_path / "renamed2.txt").exists()
            assert not (temp_path / "test2.txt").exists()


class TestCLICommand:
    """CLI命令测试."""

    def test_rename_command_basic(self) -> None:
        """测试基本重命名命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "text",
                    "--pattern",
                    "test",
                    "--replacement",
                    "renamed",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code == 0
            assert (
                "成功重命名:" in result.output or "successful" in result.output.lower()
            )
            assert (temp_path / "renamed.txt").exists()

    def test_rename_command_with_filter(self) -> None:
        """测试带过滤器的重命名命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files = [temp_path / "test1.txt", temp_path / "test2.py"]
            for file_path in files:
                file_path.write_text("test content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "text",
                    "--pattern",
                    "test",
                    "--replacement",
                    "renamed",
                    "--filter",
                    "*.txt",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code == 0
            assert (temp_path / "renamed1.txt").exists()
            assert (temp_path / "test2.py").exists()

    def test_rename_command_execute_mode(self) -> None:
        """测试执行模式命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "text",
                    "--pattern",
                    "test",
                    "--replacement",
                    "renamed",
                    "--execute",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code == 0
            assert (
                "成功重命名:" in result.output or "successful" in result.output.lower()
            )
            assert (temp_path / "renamed.txt").exists()

    def test_rename_command_skip_confirm(self) -> None:
        """测试跳过确认的命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "text",
                    "--pattern",
                    "test",
                    "--replacement",
                    "renamed",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code == 0
            assert (
                "成功重命名:" in result.output or "successful" in result.output.lower()
            )
            assert (temp_path / "renamed.txt").exists()

    def test_rename_command_no_matches(self) -> None:
        """测试没有匹配文件的命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "text",
                    "--pattern",
                    "nomatch",
                    "--replacement",
                    "renamed",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert (
                "没有找到匹配" in result.output
                or "总文件数: 0" in result.output
                or "成功重命名: 0" in result.output
                or "successful" in output_lower
            )

    def test_rename_command_invalid_pattern(self) -> None:
        """测试无效模式的命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "regex",
                    "--pattern",
                    "[invalid",
                    "--replacement",
                    "renamed",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code != 0
            error_indicators = [
                "unterminated character set",
                "invalid",
                "error",
                "错误",
            ]
            assert any(
                indicator in result.output.lower() for indicator in error_indicators
            )

    def test_rename_command_all_skipped(self) -> None:
        """测试所有文件都被跳过的命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            target_file = temp_path / "renamed.txt"
            test_file.write_text("test content")
            target_file.write_text("existing content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "text",
                    "--pattern",
                    "test",
                    "--replacement",
                    "renamed",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code == 0
            assert "跳过" in result.output or "skip" in result.output.lower()

    def test_rename_command_mixed_results(self) -> None:
        """测试混合结果的命令."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files = [temp_path / "test1.txt", temp_path / "test2.txt"]
            for file_path in files:
                file_path.write_text("test content")
            conflict_file = temp_path / "renamed1.txt"
            conflict_file.write_text("existing content")
            result = runner.invoke(
                rename_cmd,
                [
                    str(temp_path),
                    "--mode",
                    "text",
                    "--pattern",
                    "test",
                    "--replacement",
                    "renamed",
                    "--skip-confirm",
                ],
            )
            assert result.exit_code in [0, 1]
            assert (
                "成功重命名:" in result.output
                or "失败重命名:" in result.output
                or "successful" in result.output.lower()
                or "failed" in result.output.lower()
            )

    def test_rename_command_user_cancel(self) -> None:
        """测试用户取消操作."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            with patch(
                "simple_tools.core.batch_rename.smart_confirm_sync", return_value=False
            ):
                result = runner.invoke(
                    rename_cmd,
                    [
                        str(temp_path),
                        "--mode",
                        "text",
                        "--pattern",
                        "test",
                        "--replacement",
                        "renamed",
                    ],
                )
                assert result.exit_code == 0
                assert test_file.exists()
                assert not (temp_path / "renamed.txt").exists()

    def test_error_handling_with_smart_interaction(self) -> None:
        """测试带智能交互的错误处理."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")
            with patch(
                "simple_tools.core.batch_rename.smart_confirm_sync", return_value=True
            ):
                result = runner.invoke(
                    rename_cmd,
                    [
                        str(temp_path),
                        "--mode",
                        "text",
                        "--pattern",
                        "test",
                        "--replacement",
                        "renamed",
                    ],
                )
                assert result.exit_code == 0
                assert (
                    "成功重命名:" in result.output
                    or "successful" in result.output.lower()
                )
                assert (temp_path / "renamed.txt").exists()
                assert not test_file.exists()
