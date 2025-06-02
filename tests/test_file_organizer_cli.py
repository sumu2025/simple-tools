# tests/test_file_organizer.py
"""文件整理工具测试."""
import tempfile
from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from simple_tools.cli import cli


class TestFileOrganizer:
    """文件整理工具测试类."""

    def setup_method(self) -> None:
        """初始化 CLI 测试运行器。."""
        self.runner = CliRunner()

    def test_organize_by_type(self) -> None:
        """测试按类型整理."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建不同类型的文件
            Path(tmpdir, "photo.jpg").write_text("image")
            Path(tmpdir, "document.pdf").write_text("pdf")
            Path(tmpdir, "music.mp3").write_text("audio")
            Path(tmpdir, "data.txt").write_text("text")

            # 执行整理
            result = self.runner.invoke(
                cli, ["organize", tmpdir, "--mode", "type", "--execute"]
            )

            assert result.exit_code == 0
            # 检查文件是否被移动到相应目录
            assert Path(tmpdir, "图片", "photo.jpg").exists()
            assert Path(tmpdir, "文档", "document.pdf").exists()
            assert Path(tmpdir, "音频", "music.mp3").exists()
            assert Path(tmpdir, "文档", "data.txt").exists()

    def test_organize_by_date(self) -> None:
        """测试按日期整理."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = Path(tmpdir, "test.txt")
            test_file.write_text("content")

            # 执行整理
            result = self.runner.invoke(
                cli, ["organize", tmpdir, "--mode", "date", "--execute"]
            )

            assert result.exit_code == 0
            # 检查文件是否被移动到日期目录
            now = datetime.now()
            expected_path = Path(tmpdir, str(now.year), f"{now.month:02d}", "test.txt")
            assert expected_path.exists()

    def test_organize_mixed_mode(self) -> None:
        """测试混合模式整理."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "photo.jpg").write_text("image")

            # 执行整理
            result = self.runner.invoke(
                cli, ["organize", tmpdir, "--mode", "mixed", "--execute"]
            )

            assert result.exit_code == 0
            # 检查文件是否按类型和日期整理
            now = datetime.now()
            expected_path = Path(
                tmpdir, "图片", str(now.year), f"{now.month:02d}", "photo.jpg"
            )
            assert expected_path.exists()

    def test_dry_run_preview(self) -> None:
        """测试预览模式."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "test.txt").write_text("content")

            # 默认是预览模式
            result = self.runner.invoke(cli, ["organize", tmpdir])
            # 临时加入
            print(result.output)
            print(result.exit_code)
            # 临时加入
            assert result.exit_code == 0
            assert "整理计划" in result.output or "preview" in result.output.lower()
            # 文件应该还在原位置
            assert Path(tmpdir, "test.txt").exists()

    def test_skip_existing_files(self) -> None:
        """测试跳过已存在的文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建源文件
            Path(tmpdir, "test.txt").write_text("original")

            # 创建目标位置的同名文件
            docs_dir = Path(tmpdir, "文档")
            docs_dir.mkdir()
            Path(docs_dir, "test.txt").write_text("existing")

            # 执行整理
            result = self.runner.invoke(
                cli, ["organize", tmpdir, "--mode", "type", "--execute"]
            )

            assert result.exit_code == 0
            # 原文件应该还在
            assert Path(tmpdir, "test.txt").exists()
            # 目标文件内容未变
            assert Path(docs_dir, "test.txt").read_text() == "existing"
