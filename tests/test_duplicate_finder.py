"""
重复文件检测工具单元测试 - 测试find_duplicates功能
"""

import os
from pathlib import Path
import pytest
from click.testing import CliRunner
from simple_tools.core.duplicate_finder import (
    DuplicateConfig, FileInfo, DuplicateGroup, DuplicateFinder,
    format_size, display_duplicate_results, duplicates_cmd
)


class TestDataModels:
    """测试数据模型"""

    def test_duplicate_config_model(self):
        """测试DuplicateConfig模型"""
        config = DuplicateConfig(
            path="/test/path",
            recursive=True,
            min_size=1024,
            extensions=[".txt", ".jpg"]
        )

        assert config.path == "/test/path"
        assert config.recursive == True
        assert config.min_size == 1024
        assert config.extensions == [".txt", ".jpg"]

    def test_file_info_model(self):
        """测试FileInfo模型"""
        file_info = FileInfo(
            path=Path("/test/file.txt"),
            size=1024,
            hash="abc123"
        )

        assert file_info.path == Path("/test/file.txt")
        assert file_info.size == 1024
        assert file_info.hash == "abc123"

    def test_duplicate_group_model(self):
        """测试DuplicateGroup模型"""
        group = DuplicateGroup(
            hash="abc123",
            size=1024,
            count=3,
            files=[Path("/file1.txt"), Path("/file2.txt"), Path("/file3.txt")],
            potential_save=2048
        )

        assert group.hash == "abc123"
        assert group.size == 1024
        assert group.count == 3
        assert len(group.files) == 3
        assert group.potential_save == 2048


class TestDuplicateFinder:
    """测试DuplicateFinder核心功能"""

    def test_find_duplicates_basic(self, temp_dir):
        """测试基本的重复文件检测"""
        # 创建重复文件
        content = "This is duplicate content\n"
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)
        (temp_dir / "file3.txt").write_text(content)

        # 创建不同内容的文件
        (temp_dir / "unique.txt").write_text("This is unique content\n")

        # 执行检测
        config = DuplicateConfig(path=str(temp_dir))
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        # 验证结果
        assert len(duplicates) == 1
        assert duplicates[0].count == 3
        assert len(duplicates[0].files) == 3

        # 验证文件名
        file_names = [f.name for f in duplicates[0].files]
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        assert "file3.txt" in file_names

    def test_find_duplicates_no_duplicates(self, temp_dir):
        """测试没有重复文件的情况"""
        # 创建不同内容的文件
        (temp_dir / "file1.txt").write_text("Content 1")
        (temp_dir / "file2.txt").write_text("Content 2")
        (temp_dir / "file3.txt").write_text("Content 3")

        # 执行检测
        config = DuplicateConfig(path=str(temp_dir))
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        # 验证结果
        assert len(duplicates) == 0

    def test_find_duplicates_empty_directory(self, temp_dir):
        """测试空目录"""
        config = DuplicateConfig(path=str(temp_dir))
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        assert len(duplicates) == 0

    def test_find_duplicates_with_subdirectories(self, temp_dir):
        """测试递归扫描子目录"""
        # 创建子目录结构
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        nested = subdir / "nested"
        nested.mkdir()

        # 创建重复文件
        content = "Duplicate content in subdirs\n"
        (temp_dir / "file1.txt").write_text(content)
        (subdir / "file2.txt").write_text(content)
        (nested / "file3.txt").write_text(content)

        # 递归扫描
        config = DuplicateConfig(path=str(temp_dir), recursive=True)
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        assert len(duplicates) == 1
        assert duplicates[0].count == 3

    def test_find_duplicates_no_recursive(self, temp_dir):
        """测试非递归扫描"""
        # 创建子目录
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        # 创建重复文件
        content = "Same content\n"
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)
        (subdir / "file3.txt").write_text(content)  # 子目录中的文件

        # 非递归扫描
        config = DuplicateConfig(path=str(temp_dir), recursive=False)
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        # 应该只找到顶层的两个重复文件
        assert len(duplicates) == 1
        assert duplicates[0].count == 2

    def test_find_duplicates_min_size_filter(self, temp_dir):
        """测试最小文件大小过滤"""
        # 创建小文件（会被过滤）
        small_content = "A"
        (temp_dir / "small1.txt").write_text(small_content)
        (temp_dir / "small2.txt").write_text(small_content)

        # 创建大文件
        large_content = "B" * 1000
        (temp_dir / "large1.txt").write_text(large_content)
        (temp_dir / "large2.txt").write_text(large_content)

        # 设置最小文件大小为100字节
        config = DuplicateConfig(path=str(temp_dir), min_size=100)
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        # 应该只找到大文件的重复
        assert len(duplicates) == 1
        assert duplicates[0].count == 2
        file_names = [f.name for f in duplicates[0].files]
        assert "large1.txt" in file_names
        assert "large2.txt" in file_names

    def test_find_duplicates_extension_filter(self, temp_dir):
        """测试文件扩展名过滤"""
        # 创建不同类型的重复文件
        content = "Same content\n"
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)
        (temp_dir / "file3.jpg").write_text(content)
        (temp_dir / "file4.jpg").write_text(content)
        (temp_dir / "file5.doc").write_text(content)

        # 只检测txt文件
        config = DuplicateConfig(path=str(temp_dir), extensions=[".txt"])
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        # 应该只找到txt文件的重复
        assert len(duplicates) == 1
        assert duplicates[0].count == 2
        for file_path in duplicates[0].files:
            assert file_path.suffix == ".txt"

    def test_find_duplicates_multiple_groups(self, temp_dir):
        """测试多组重复文件"""
        # 第一组重复文件
        content1 = "Content group 1\n"
        (temp_dir / "group1_file1.txt").write_text(content1)
        (temp_dir / "group1_file2.txt").write_text(content1)

        # 第二组重复文件（更大的文件）
        content2 = "Content group 2\n" * 100
        (temp_dir / "group2_file1.txt").write_text(content2)
        (temp_dir / "group2_file2.txt").write_text(content2)
        (temp_dir / "group2_file3.txt").write_text(content2)

        # 执行检测
        config = DuplicateConfig(path=str(temp_dir))
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        # 应该找到两组重复文件
        assert len(duplicates) == 2

        # 验证按可节省空间排序（大的在前）
        assert duplicates[0].potential_save > duplicates[1].potential_save

    def test_calculate_file_hash(self, temp_dir):
        """测试文件哈希计算"""
        # 创建测试文件
        file_path = temp_dir / "test.txt"
        file_path.write_text("Test content for hash")

        # 计算哈希
        config = DuplicateConfig(path=str(temp_dir))
        finder = DuplicateFinder(config)
        hash1 = finder._calculate_file_hash(file_path)
        hash2 = finder._calculate_file_hash(file_path)

        # 相同文件的哈希值应该相同
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5哈希长度

    def test_potential_save_calculation(self, temp_dir):
        """测试可节省空间计算"""
        # 创建3个相同的1KB文件
        content = "X" * 1024
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)
        (temp_dir / "file3.txt").write_text(content)

        # 执行检测
        config = DuplicateConfig(path=str(temp_dir))
        finder = DuplicateFinder(config)
        duplicates = finder.find_duplicates()

        # 验证可节省空间计算（保留1个，删除2个）
        assert len(duplicates) == 1
        assert duplicates[0].potential_save == 1024 * 2


class TestCLICommand:
    """测试CLI命令"""

    def test_duplicates_command_basic(self, temp_dir, cli_runner):
        """测试基本的duplicates命令"""
        # 创建重复文件
        content = "Duplicate content\n"
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)

        # 创建模拟的配置对象
        mock_ctx = {"config": type('Config', (), {"verbose": False})()}

        # 运行命令
        result = cli_runner.invoke(duplicates_cmd, [str(temp_dir)], obj=mock_ctx)

        assert result.exit_code == 0
        assert "扫描目录:" in result.output
        assert "发现 1 组重复文件" in result.output
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output

    def test_duplicates_command_no_duplicates(self, temp_dir, cli_runner):
        """测试没有重复文件的情况"""
        # 创建不同的文件
        (temp_dir / "file1.txt").write_text("Content 1")
        (temp_dir / "file2.txt").write_text("Content 2")

        mock_ctx = {"config": type('Config', (), {"verbose": False})()}

        result = cli_runner.invoke(duplicates_cmd, [str(temp_dir)], obj=mock_ctx)

        assert result.exit_code == 0
        assert "未发现重复文件" in result.output

    def test_duplicates_command_with_options(self, temp_dir, cli_runner):
        """测试带选项的命令"""
        # 创建测试文件
        content = "Test content\n"
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)
        (temp_dir / "file3.jpg").write_text(content)
        (temp_dir / "file4.jpg").write_text(content)

        mock_ctx = {"config": type('Config', (), {"verbose": False})()}

        # 测试扩展名过滤
        result = cli_runner.invoke(
            duplicates_cmd,
            [str(temp_dir), "-e", ".txt"],
            obj=mock_ctx
        )

        assert result.exit_code == 0
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
        assert "file3.jpg" not in result.output

    def test_duplicates_command_show_commands(self, temp_dir, cli_runner):
        """测试显示删除命令建议"""
        # 创建重复文件
        content = "Duplicate\n"
        (temp_dir / "dup1.txt").write_text(content)
        (temp_dir / "dup2.txt").write_text(content)

        mock_ctx = {"config": type('Config', (), {"verbose": False})()}

        result = cli_runner.invoke(
            duplicates_cmd,
            [str(temp_dir), "--show-commands"],
            obj=mock_ctx
        )

        assert result.exit_code == 0
        assert "建议保留:" in result.output
        assert "rm " in result.output
        assert "警告：删除文件前请确认" in result.output

    def test_duplicates_command_no_recursive(self, temp_dir, cli_runner):
        """测试非递归选项"""
        # 创建子目录和文件
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        content = "Same\n"
        (temp_dir / "file1.txt").write_text(content)
        (temp_dir / "file2.txt").write_text(content)
        (subdir / "file3.txt").write_text(content)

        mock_ctx = {"config": type('Config', (), {"verbose": False})()}

        # 使用 -n 选项（非递归）
        result = cli_runner.invoke(
            duplicates_cmd,
            [str(temp_dir), "-n"],
            obj=mock_ctx
        )

        assert result.exit_code == 0
        assert "仅顶层目录" in result.output
        # 应该只找到顶层的2个文件
        assert "2 个文件" in result.output

    def test_duplicates_command_min_size(self, temp_dir, cli_runner):
        """测试最小文件大小选项"""
        # 创建小文件
        (temp_dir / "small1.txt").write_text("A")
        (temp_dir / "small2.txt").write_text("A")

        mock_ctx = {"config": type('Config', (), {"verbose": False})()}

        # 设置最小大小为1MB
        result = cli_runner.invoke(
            duplicates_cmd,
            [str(temp_dir), "-s", "1048576"],
            obj=mock_ctx
        )

        assert result.exit_code == 0
        assert "未发现重复文件" in result.output


class TestUtilityFunctions:
    """测试工具函数"""

    def test_format_size_function(self):
        """测试format_size函数"""
        # 这个函数与file_tool中的相同，做基本测试
        assert format_size(0) == "0 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1048576) == "1.0 MB"

    def test_display_duplicate_results(self, capsys):
        """测试结果显示函数"""
        # 创建测试数据
        groups = [
            DuplicateGroup(
                hash="abc123",
                size=1024,
                count=2,
                files=[Path("/file1.txt"), Path("/file2.txt")],
                potential_save=1024
            )
        ]

        # 调用显示函数
        display_duplicate_results(
            duplicate_groups=groups,
            scan_path="/test/path",
            total_files=10,
            recursive=True,
            show_commands=False
        )

        # 捕获输出
        captured = capsys.readouterr()

        assert "扫描目录: /test/path" in captured.out
        assert "递归扫描" in captured.out
        assert "发现 1 组重复文件" in captured.out
        assert "file1.txt" in captured.out
        assert "file2.txt" in captured.out
