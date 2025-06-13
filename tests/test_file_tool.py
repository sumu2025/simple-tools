"""文件工具单元测试 - 测试list_files功能."""

from pathlib import Path
from typing import Any

import pytest

from simple_tools.core.file_tool import format_size, format_time, list_cmd, list_files


class TestFormatFunctions:
    """测试格式化辅助函数."""

    def test_format_size(self) -> None:
        """测试文件大小格式化."""
        assert format_size(0) == "0 B"
        assert format_size(512) == "512.0 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"
        assert format_size(1048576) == "1.0 MB"
        assert format_size(1572864) == "1.5 MB"
        assert format_size(1073741824) == "1.0 GB"

    def test_format_time(self) -> None:
        """测试时间格式化."""
        # 使用一个固定的时间戳进行测试
        timestamp = 1735123200  # 2024-12-25 08:00:00
        formatted = format_time(timestamp)
        assert "2024-12-25" in formatted
        assert ":" in formatted  # 应该包含时间部分


class TestListFiles:
    """测试list_files核心功能."""

    def test_list_empty_directory(self, temp_dir: Path) -> None:
        """测试列出空目录."""
        result = list_files(str(temp_dir))
        assert result == []

    def test_list_files_basic(self, temp_dir: Path) -> None:
        """测试基本文件列表功能."""
        # 创建测试文件和目录
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "subdir").mkdir()

        result = list_files(str(temp_dir))

        # 验证结果
        assert len(result) == 3
        names = [item["name"] for item in result]
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "subdir" in names

        # 验证目录在前
        assert result[0]["name"] == "subdir"
        assert result[0]["is_dir"]

        # 验证文件按名称排序
        assert result[1]["name"] == "file1.txt"
        assert result[2]["name"] == "file2.txt"

    def test_list_files_with_hidden(self, temp_dir: Path) -> None:
        """测试隐藏文件显示功能."""
        # 创建普通文件和隐藏文件
        (temp_dir / "visible.txt").write_text("visible")
        (temp_dir / ".hidden").write_text("hidden")
        (temp_dir / ".config").write_text("config")

        # 默认不显示隐藏文件
        result = list_files(str(temp_dir), show_hidden=False)
        assert len(result) == 1
        assert result[0]["name"] == "visible.txt"

        # 显示隐藏文件
        result = list_files(str(temp_dir), show_hidden=True)
        assert len(result) == 3
        names = [item["name"] for item in result]
        assert ".hidden" in names
        assert ".config" in names
        assert "visible.txt" in names

    def test_list_files_with_details(self, temp_dir: Path) -> None:
        """测试详细信息显示功能."""
        # 创建测试文件
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")

        # 创建目录
        dir_path = temp_dir / "testdir"
        dir_path.mkdir()

        # 获取详细信息
        result = list_files(str(temp_dir), show_details=True)

        # 验证文件详细信息
        file_info = next(item for item in result if item["name"] == "test.txt")
        assert "size" in file_info
        assert "size_formatted" in file_info
        assert "modified" in file_info
        assert "modified_formatted" in file_info
        assert file_info["size"] > 0
        assert "B" in file_info["size_formatted"] or "KB" in file_info["size_formatted"]

        # 验证目录没有详细信息（即使在详细模式下）
        dir_info = next(item for item in result if item["name"] == "testdir")
        assert "size" not in dir_info

    def test_list_files_sorting(self, temp_dir: Path) -> None:
        """测试文件排序功能."""
        # 创建混合大小写的文件和目录
        (temp_dir / "Apple.txt").write_text("a")
        (temp_dir / "banana.txt").write_text("b")
        (temp_dir / "Cherry").mkdir()
        (temp_dir / "date.txt").write_text("d")
        (temp_dir / "Elderberry").mkdir()

        result = list_files(str(temp_dir))
        names = [item["name"] for item in result]

        # 验证目录在前
        assert result[0]["is_dir"]
        assert result[1]["is_dir"]
        assert not result[2]["is_dir"]

        # 验证按名称排序（不区分大小写）
        assert names == ["Cherry", "Elderberry", "Apple.txt", "banana.txt", "date.txt"]

    def test_list_nonexistent_directory(self) -> None:
        """测试不存在的目录."""
        from simple_tools.utils.errors import ToolError

        with pytest.raises(ToolError) as exc_info:
            list_files("/nonexistent/directory")

        assert "不存在" in str(exc_info.value)

    def test_list_file_not_directory(self, temp_dir: Path) -> None:
        """测试路径不是目录的情况."""
        from simple_tools.utils.errors import ToolError

        # 创建一个文件
        file_path = temp_dir / "not_a_dir.txt"
        file_path.write_text("content")

        with pytest.raises(ToolError) as exc_info:
            list_files(str(file_path))

        assert "不是一个目录" in str(exc_info.value)

    def test_list_permission_error(self, temp_dir: Path, monkeypatch: Any) -> None:
        """测试权限错误处理."""
        from simple_tools.utils.errors import ToolError

        # 模拟 Path.iterdir() 权限错误
        def mock_iterdir(self: Path) -> list[Path]:
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        with pytest.raises(ToolError) as exc_info:
            list_files(str(temp_dir))

        # 验证错误信息
        assert exc_info.value.error_code == "PERMISSION_DENIED"
        assert "权限" in exc_info.value.message


class TestListCommand:
    """测试CLI命令."""

    def test_list_command_basic(self, temp_dir: Path, cli_runner: Any) -> None:
        """测试基本的list命令."""
        # 创建测试文件
        (temp_dir / "test.txt").write_text("content")
        (temp_dir / "subdir").mkdir()

        # 创建模拟的配置对象
        mock_ctx = {"config": type("Config", (), {"verbose": False})()}

        # 运行命令
        result = cli_runner.invoke(list_cmd, [str(temp_dir)], obj=mock_ctx)

        assert result.exit_code == 0
        assert "目录:" in result.output
        assert "[文件] test.txt" in result.output
        assert "[目录] subdir" in result.output
        assert "总计: 2 个项目" in result.output

    def test_list_command_with_all_option(
        self, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试带 --all 选项的命令."""
        # 创建隐藏文件
        (temp_dir / ".hidden").write_text("hidden")
        (temp_dir / "visible.txt").write_text("visible")

        mock_ctx = {"config": type("Config", (), {"verbose": False})()}

        # 不带 --all 选项
        result = cli_runner.invoke(list_cmd, [str(temp_dir)], obj=mock_ctx)
        assert ".hidden" not in result.output
        assert "visible.txt" in result.output

        # 带 --all 选项
        result = cli_runner.invoke(list_cmd, [str(temp_dir), "--all"], obj=mock_ctx)
        assert ".hidden" in result.output
        assert "visible.txt" in result.output

    def test_list_command_with_long_option(
        self, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试带 --long 选项的命令."""
        # 创建测试文件
        (temp_dir / "test.txt").write_text("test content here")

        mock_ctx = {"config": type("Config", (), {"verbose": False})()}

        result = cli_runner.invoke(list_cmd, [str(temp_dir), "--long"], obj=mock_ctx)

        assert result.exit_code == 0
        assert "[文件]" in result.output
        assert "test.txt" in result.output
        assert "B" in result.output or "KB" in result.output  # 文件大小
        assert ":" in result.output  # 时间格式

    def test_list_command_empty_directory(
        self, temp_dir: Path, cli_runner: Any
    ) -> None:
        """测试空目录的命令输出."""
        mock_ctx = {"config": type("Config", (), {"verbose": False})()}

        result = cli_runner.invoke(list_cmd, [str(temp_dir)], obj=mock_ctx)

        assert result.exit_code == 0
        assert "目录为空" in result.output

    def test_list_command_default_current_directory(
        self, cli_runner: Any, monkeypatch: Any
    ) -> None:
        """测试默认使用当前目录."""
        mock_ctx = {"config": type("Config", (), {"verbose": False})()}

        # 改变当前目录到临时目录
        Path.cwd()

        # 模拟list_files函数返回一些文件
        def mock_list_files(directory: str, **kwargs: Any) -> list[dict[str, Any]]:
            return [
                {"name": "file1.txt", "is_dir": False, "path": "file1.txt"},
                {"name": "dir1", "is_dir": True, "path": "dir1"},
            ]

        monkeypatch.setattr("simple_tools.core.file_tool.list_files", mock_list_files)

        # 不提供路径参数，应该使用当前目录
        result = cli_runner.invoke(list_cmd, [], obj=mock_ctx)

        assert result.exit_code == 0
        assert "file1.txt" in result.output
        assert "dir1" in result.output

    def test_list_command_error_handling(self, cli_runner: Any) -> None:
        """测试错误处理."""
        mock_ctx = {"config": type("Config", (), {"verbose": False})()}

        # 测试不存在的目录
        result = cli_runner.invoke(list_cmd, ["/nonexistent/path"], obj=mock_ctx)

        assert result.exit_code != 0
        assert "Error" in result.output
