"""批量重命名工具单元测试 - 测试batch_rename功能."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from simple_tools.core.batch_rename import (
    BatchRenameTool,
    RenameConfig,
    RenameItem,
    RenameResult,
    rename_cmd,
)


class TestDataModels:
    """测试数据模型."""

    def test_rename_config_model(self) -> None:
        """测试RenameConfig模型."""
        config = RenameConfig(
            pattern="old:new",
            path="/test/path",
            filter_pattern="*.txt",
            number_mode=False,
            dry_run=True,
            skip_confirm=False,
        )

        assert config.pattern == "old:new"
        assert config.path == "/test/path"
        assert config.filter_pattern == "*.txt"
        assert not config.number_mode
        assert config.dry_run
        assert not config.skip_confirm

    def test_rename_item_model(self) -> None:
        """测试RenameItem模型."""
        item = RenameItem(
            old_path=Path("/old/file.txt"),
            new_path=Path("/new/file.txt"),
            status="success",
            error=None,
        )

        assert item.old_path == Path("/old/file.txt")
        assert item.new_path == Path("/new/file.txt")
        assert item.status == "success"
        assert item.error is None

    def test_rename_result_model(self) -> None:
        """测试RenameResult模型."""
        result = RenameResult(total=10, success=7, failed=1, skipped=2, items=[])

        assert result.total == 10
        assert result.success == 7
        assert result.failed == 1
        assert result.skipped == 2
        assert result.items == []


class TestBatchRenameTool:
    """测试BatchRenameTool核心功能."""

    def test_scan_files_basic(self, temp_dir: Path) -> None:
        """测试基本文件扫描."""
        # 创建测试文件
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "image.jpg").write_text("image")
        (temp_dir / "subdir").mkdir()

        # 扫描所有文件
        config = RenameConfig(pattern="old:new", path=str(temp_dir))
        tool = BatchRenameTool(config)
        files = tool._scan_files()

        assert len(files) == 3
        file_names = [f.name for f in files]
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        assert "image.jpg" in file_names

    def test_scan_files_with_filter(self, temp_dir: Path) -> None:
        """测试带过滤器的文件扫描."""
        # 创建不同类型的文件
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "image.jpg").write_text("image")
        (temp_dir / "doc.pdf").write_text("doc")

        # 只扫描txt文件
        config = RenameConfig(
            pattern="old:new", path=str(temp_dir), filter_pattern="*.txt"
        )
        tool = BatchRenameTool(config)
        files = tool._scan_files()

        assert len(files) == 2
        for file in files:
            assert file.suffix == ".txt"

    def test_parse_pattern_text_mode(self) -> None:
        """测试文本替换模式的模式解析."""
        config = RenameConfig(pattern="old:new", number_mode=False)
        tool = BatchRenameTool(config)
        old_text, new_text = tool._parse_pattern("old:new")

        assert old_text == "old"
        assert new_text == "new"

    def test_parse_pattern_number_mode(self) -> None:
        """测试序号模式的模式解析."""
        config = RenameConfig(pattern="prefix", number_mode=True)
        tool = BatchRenameTool(config)
        old_text, new_text = tool._parse_pattern("prefix")

        assert old_text == ""
        assert new_text == "prefix"

    def test_parse_pattern_invalid_format(self) -> None:
        """测试无效模式格式."""
        config = RenameConfig(pattern="invalid", number_mode=False)
        tool = BatchRenameTool(config)

        with pytest.raises(ValueError) as exc_info:
            tool._parse_pattern("invalid")

        assert "old:new" in str(exc_info.value)

    def test_generate_new_name_text_mode(self, temp_dir: Path) -> None:
        """测试文本替换模式的新名称生成."""
        file_path = temp_dir / "old_file.txt"
        file_path.write_text("content")

        config = RenameConfig(pattern="old:new", number_mode=False)
        tool = BatchRenameTool(config)
        new_path, changed = tool._generate_new_name(file_path, 0)

        assert new_path.name == "new_file.txt"
        assert changed

    def test_generate_new_name_text_mode_no_match(self, temp_dir: Path) -> None:
        """测试文本替换模式无匹配的情况."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("content")

        config = RenameConfig(pattern="old:new", number_mode=False)
        tool = BatchRenameTool(config)
        new_path, changed = tool._generate_new_name(file_path, 0)

        assert new_path.name == "file.txt"  # 没有改变
        assert not changed

    def test_generate_new_name_number_mode(self, temp_dir: Path) -> None:
        """测试序号模式的新名称生成."""
        file_path = temp_dir / "image.jpg"
        file_path.write_text("content")

        config = RenameConfig(pattern="photo", number_mode=True)
        tool = BatchRenameTool(config)

        # 测试多个文件的序号
        new_path1, changed1 = tool._generate_new_name(file_path, 0)
        new_path2, changed2 = tool._generate_new_name(file_path, 1)
        new_path3, changed3 = tool._generate_new_name(file_path, 99)

        assert new_path1.name == "photo_001.jpg"
        assert new_path2.name == "photo_002.jpg"
        assert new_path3.name == "photo_100.jpg"
        assert all([changed1, changed2, changed3])

    def test_check_conflicts_no_change(self, temp_dir: Path) -> None:
        """测试文件名无变化的冲突检查."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("content")

        # 创建一个文件名不会改变的重命名项
        item = RenameItem(
            old_path=file_path, new_path=file_path, status="pending"  # 相同路径
        )

        config = RenameConfig(pattern="old:new", number_mode=False)
        tool = BatchRenameTool(config)
        items = tool._check_conflicts_and_changes([item])

        assert items[0].status == "skipped"
        assert "不包含要替换的文本" in items[0].error

    def test_check_conflicts_file_exists(self, temp_dir: Path) -> None:
        """测试目标文件已存在的冲突检查."""
        # 创建源文件和目标文件
        old_file = temp_dir / "old.txt"
        new_file = temp_dir / "new.txt"
        old_file.write_text("old content")
        new_file.write_text("new content")

        item = RenameItem(old_path=old_file, new_path=new_file, status="pending")

        config = RenameConfig(pattern="old:new")
        tool = BatchRenameTool(config)
        items = tool._check_conflicts_and_changes([item])

        assert items[0].status == "skipped"
        assert "目标文件已存在" in items[0].error

    def test_execute_rename_success(self, temp_dir: Path) -> None:
        """测试成功执行重命名."""
        # 创建测试文件
        old_file = temp_dir / "old_file.txt"
        old_file.write_text("content")

        # 创建重命名项
        item = RenameItem(
            old_path=old_file, new_path=temp_dir / "new_file.txt", status="pending"
        )

        config = RenameConfig(pattern="old:new")
        tool = BatchRenameTool(config)
        result = tool.execute_rename([item])

        # 验证结果
        assert result.total == 1
        assert result.success == 1
        assert result.failed == 0
        assert result.skipped == 0

        # 验证文件系统
        assert not old_file.exists()
        assert (temp_dir / "new_file.txt").exists()

    def test_execute_rename_with_skipped(self, temp_dir: Path) -> None:
        """测试包含跳过项的执行."""
        # 创建测试文件
        file1 = temp_dir / "file1.txt"
        file1.write_text("content1")

        # 创建重命名项，一个正常，一个跳过
        items = [
            RenameItem(
                old_path=file1, new_path=temp_dir / "renamed1.txt", status="pending"
            ),
            RenameItem(
                old_path=temp_dir / "file2.txt",
                new_path=temp_dir / "renamed2.txt",
                status="skipped",
                error="文件不存在",
            ),
        ]

        config = RenameConfig(pattern="old:new")
        tool = BatchRenameTool(config)
        result = tool.execute_rename(items)

        assert result.total == 2
        assert result.success == 1
        assert result.failed == 0
        assert result.skipped == 1

    def test_run_text_replace_mode(self, temp_dir: Path, cli_runner: Any) -> None:
        """测试文本替换模式的完整流程."""
        # 创建测试文件
        (temp_dir / "old_file1.txt").write_text("content1")
        (temp_dir / "old_file2.txt").write_text("content2")
        (temp_dir / "new_file.txt").write_text("other")

        with patch("click.confirm", return_value=True):
            config = RenameConfig(
                pattern="old:new", path=str(temp_dir), dry_run=True, skip_confirm=False
            )

            tool = BatchRenameTool(config)
            result = tool.run()

        # 验证结果
        assert result.total == 3
        assert result.success == 2
        assert result.skipped == 1  # new_file.txt不包含"old"

    def test_run_number_mode(self, temp_dir: Path, cli_runner: Any) -> None:
        """测试序号模式的完整流程."""
        # 创建测试文件
        (temp_dir / "img1.jpg").write_text("image1")
        (temp_dir / "img2.jpg").write_text("image2")
        (temp_dir / "img3.jpg").write_text("image3")

        with patch("click.confirm", return_value=True):
            config = RenameConfig(
                pattern="photo",
                path=str(temp_dir),
                number_mode=True,
                dry_run=True,
                skip_confirm=False,
            )

            tool = BatchRenameTool(config)
            result = tool.run()

        # 验证结果
        assert result.total == 3
        assert result.success == 3

        # 验证新文件名
        assert (temp_dir / "photo_001.jpg").exists()
        assert (temp_dir / "photo_002.jpg").exists()
        assert (temp_dir / "photo_003.jpg").exists()


class TestCLICommand:
    """测试CLI命令."""

    @patch("click.confirm", return_value=True)
    def test_rename_command_basic(
        self, mock_confirm: Any, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试基本的rename命令（预览模式）."""
        # 创建测试文件
        (temp_dir / "old_file.txt").write_text("content")

        # 运行命令（预览模式）
        result = cli_runner.invoke(rename_cmd, ["old:new", "-p", str(temp_dir)])

        assert result.exit_code == 0
        assert "扫描目录:" in result.output
        assert "重命名预览：" in result.output
        assert "old_file.txt" in result.output
        assert "new_file.txt" in result.output
        assert "正在执行重命名" in result.output

    @patch("click.confirm", return_value=True)
    def test_rename_command_number_mode(
        self, mock_confirm: Any, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试序号模式命令."""
        # 创建测试文件
        (temp_dir / "img1.jpg").write_text("image1")
        (temp_dir / "img2.jpg").write_text("image2")

        # 使用序号模式
        result = cli_runner.invoke(rename_cmd, ["photo", "-p", str(temp_dir), "-n"])

        assert result.exit_code == 0
        assert "photo_001.jpg" in result.output
        assert "photo_002.jpg" in result.output
        assert "正在执行重命名" in result.output

    @patch("click.confirm", return_value=True)
    def test_rename_command_with_filter(
        self, mock_confirm: Any, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试带文件过滤的命令."""
        # 创建不同类型的文件
        (temp_dir / "old_file.txt").write_text("text")
        (temp_dir / "old_image.jpg").write_text("image")

        # 只处理txt文件
        result = cli_runner.invoke(
            rename_cmd, ["old:new", "-p", str(temp_dir), "-f", "*.txt"]
        )

        assert result.exit_code == 0
        assert "old_file.txt" in result.output
        assert "new_file.txt" in result.output
        assert "old_image.jpg" not in result.output
        assert "正在执行重命名" in result.output

    def test_rename_command_execute_mode(self, temp_dir: Path, cli_runner: Any) -> None:
        """测试直接执行模式."""
        # 创建测试文件
        (temp_dir / "old_file.txt").write_text("content")

        # 使用 --execute 选项（不需要确认）
        result = cli_runner.invoke(
            rename_cmd, ["old:new", "-p", str(temp_dir), "--execute"]
        )

        assert result.exit_code == 0
        assert "正在执行重命名" in result.output
        assert "✓" in result.output

        # 验证文件系统
        assert not (temp_dir / "old_file.txt").exists()
        assert (temp_dir / "new_file.txt").exists()

    def test_rename_command_skip_confirm(self, temp_dir: Path, cli_runner: Any) -> None:
        """测试跳过确认选项."""
        # 创建测试文件
        (temp_dir / "old_file.txt").write_text("content")

        # 使用 -y 选项跳过确认
        result = cli_runner.invoke(rename_cmd, ["old:new", "-p", str(temp_dir), "-y"])

        assert result.exit_code == 0
        assert "确认执行重命名？" not in result.output
        assert "正在执行重命名" in result.output

    def test_rename_command_no_matches(self, temp_dir: Path, cli_runner: Any) -> None:
        """测试没有匹配文件的情况."""
        # 创建不匹配的文件
        (temp_dir / "file.txt").write_text("content")

        # 使用不会匹配的过滤器
        result = cli_runner.invoke(
            rename_cmd, ["old:new", "-p", str(temp_dir), "-f", "*.jpg"]
        )

        assert result.exit_code == 0
        assert "没有找到匹配的文件" in result.output

    def test_rename_command_invalid_pattern(self, cli_runner: Any) -> None:
        """测试无效的重命名模式."""
        # 文本模式下没有使用冒号分隔
        result = cli_runner.invoke(rename_cmd, ["invalid_pattern"])

        assert result.exit_code != 0
        assert "错误" in result.output

    def test_rename_command_all_skipped(self, temp_dir: Path, cli_runner: Any) -> None:
        """测试所有文件都被跳过的情况."""
        # 创建不包含要替换文本的文件
        (temp_dir / "file1.txt").write_text("content")
        (temp_dir / "file2.txt").write_text("content")

        # 尝试替换不存在的文本
        result = cli_runner.invoke(rename_cmd, ["old:new", "-p", str(temp_dir)])

        assert result.exit_code == 0
        assert "没有可以重命名的文件" in result.output

    @patch("click.confirm", return_value=True)
    def test_rename_command_mixed_results(
        self, mock_confirm: Any, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试混合结果（部分成功、部分跳过）."""
        # 创建测试文件
        (temp_dir / "old_file1.txt").write_text("content1")
        (temp_dir / "old_file2.txt").write_text("content2")
        (temp_dir / "new_file.txt").write_text("other")  # 不包含"old"

        result = cli_runner.invoke(rename_cmd, ["old:new", "-p", str(temp_dir)])

        assert result.exit_code == 0
        assert "成功: 2 个文件" in result.output
        assert "跳过: 1 个文件" in result.output

    @patch("click.confirm", return_value=False)
    def test_rename_command_user_cancel(
        self, mock_confirm: Any, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试用户取消操作."""
        # 创建测试文件
        (temp_dir / "old_file.txt").write_text("content")

        # 运行命令，用户选择取消
        result = cli_runner.invoke(rename_cmd, ["old:new", "-p", str(temp_dir)])

        assert result.exit_code == 0
        assert "操作已取消" in result.output
        # 确保文件没有被重命名
        assert (temp_dir / "old_file.txt").exists()
        assert not (temp_dir / "new_file.txt").exists()
