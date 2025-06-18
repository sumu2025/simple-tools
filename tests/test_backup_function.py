"""测试文本替换备份功能."""

import shutil
from pathlib import Path

from simple_tools.core.text_replace import backup_files


class TestBackupFunction:
    """测试备份功能."""

    def test_backup_files_empty_list(self) -> None:
        """测试空文件列表."""
        result = backup_files([])
        assert result is None

    def test_backup_files_success(self, tmp_path: Path) -> None:
        """测试成功备份文件."""
        # 创建测试文件
        test_file1 = tmp_path / "test1.txt"
        test_file1.write_text("Test content 1")

        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("Test content 2")

        # 执行备份
        files = [test_file1, test_file2]
        backup_dir = backup_files(files)

        # 验证备份
        assert backup_dir is not None
        assert backup_dir.exists()
        assert backup_dir.is_dir()

        # 检查备份信息文件
        info_file = backup_dir / "backup_info.json"
        assert info_file.exists()

        # 清理备份目录
        if backup_dir.exists():
            shutil.rmtree(backup_dir.parent)

    def test_backup_with_subdirectories(self, tmp_path: Path) -> None:
        """测试带子目录的文件备份."""
        # 创建带子目录的文件结构
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        file1 = tmp_path / "file1.txt"
        file1.write_text("Content 1")

        file2 = subdir / "file2.txt"
        file2.write_text("Content 2")

        # 改变工作目录以测试相对路径
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # 使用相对路径执行备份
            files = [Path("file1.txt"), Path("subdir/file2.txt")]
            backup_dir = backup_files(files)

            # 验证
            assert backup_dir is not None

            # 检查备份的文件结构是否保持
            backed_up_file1 = backup_dir / "file1.txt"
            backed_up_file2 = backup_dir / "subdir" / "file2.txt"

            assert backed_up_file1.exists()
            assert backed_up_file2.exists()
            assert backed_up_file1.read_text() == "Content 1"
            assert backed_up_file2.read_text() == "Content 2"

        finally:
            os.chdir(original_cwd)
            # 清理
            if backup_dir and backup_dir.exists():
                shutil.rmtree(backup_dir.parent)
