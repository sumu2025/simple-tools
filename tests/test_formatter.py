# tests/test_formatter.py
"""输出格式化功能的测试."""
import csv
import json
from io import StringIO

import pytest

from simple_tools.utils.formatter import (
    DuplicateData,
    FileListData,
    OutputFormat,
    format_output,
)


class TestFormatter:
    """输出格式化测试类."""

    def test_file_list_plain_format(self) -> None:
        """测试文件列表的纯文本格式输出."""
        # 准备测试数据
        data = FileListData(
            path="/test/path",
            total=2,
            files=[
                {"name": "file1.txt", "size": 1024, "type": "file"},
                {"name": "file2.py", "size": 2048, "type": "file"},
            ],
        )

        # 执行格式化
        result = format_output(data, OutputFormat.PLAIN)

        # 验证输出包含文件名
        assert "file1.txt" in result
        assert "file2.py" in result

    def test_file_list_json_format(self) -> None:
        """测试文件列表的JSON格式输出."""
        # 准备测试数据
        data = FileListData(
            path="/test/path",
            total=2,
            files=[
                {"name": "file1.txt", "size": 1024, "type": "file"},
                {"name": "file2.py", "size": 2048, "type": "file"},
            ],
        )

        # 执行格式化
        result = format_output(data, OutputFormat.JSON)

        # 验证JSON格式
        parsed = json.loads(result)
        assert parsed["path"] == "/test/path"
        assert parsed["total"] == 2
        assert len(parsed["files"]) == 2
        assert parsed["files"][0]["name"] == "file1.txt"

    def test_file_list_csv_format(self) -> None:
        """测试文件列表的CSV格式输出."""
        # 准备测试数据
        data = FileListData(
            path="/test/path",
            total=2,
            files=[
                {"name": "file1.txt", "size": 1024, "type": "file"},
                {"name": "file2.py", "size": 2048, "type": "file"},
            ],
        )

        # 执行格式化
        result = format_output(data, OutputFormat.CSV)

        # 验证CSV格式
        reader = csv.DictReader(StringIO(result))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["name"] == "file1.txt"
        assert rows[0]["size"] == "1024"

    def test_duplicates_json_format(self) -> None:
        """测试重复文件的JSON格式输出."""
        # 准备测试数据
        data = DuplicateData(
            total_groups=1,
            total_size_saved=2048,
            groups=[
                {
                    "hash": "abc123",
                    "size": 1024,
                    "count": 2,
                    "files": ["/path/file1.txt", "/path/file2.txt"],
                }
            ],
        )

        # 执行格式化
        result = format_output(data, OutputFormat.JSON)

        # 验证JSON格式
        parsed = json.loads(result)
        assert parsed["total_groups"] == 1
        assert parsed["total_size_saved"] == 2048
        assert len(parsed["groups"]) == 1
        assert parsed["groups"][0]["count"] == 2

    def test_duplicates_csv_format(self) -> None:
        """测试重复文件的CSV格式输出."""
        # 准备测试数据
        data = DuplicateData(
            total_groups=2,
            total_size_saved=3072,
            groups=[
                {
                    "hash": "abc123",
                    "size": 1024,
                    "count": 2,
                    "files": ["/path/file1.txt", "/path/file2.txt"],
                },
                {
                    "hash": "def456",
                    "size": 2048,
                    "count": 3,
                    "files": ["/path/a.jpg", "/path/b.jpg", "/path/c.jpg"],
                },
            ],
        )

        # 执行格式化
        result = format_output(data, OutputFormat.CSV)

        # 验证CSV格式
        lines = result.strip().split("\n")
        assert lines[0].startswith("hash,size,count,")  # 头部
        assert "abc123,1024,2," in lines[1]
        assert "def456,2048,3," in lines[2]

    def test_unsupported_format_raises_error(self) -> None:
        """测试不支持的格式抛出异常."""
        data = FileListData(path="/", total=0, files=[])

        with pytest.raises(ValueError, match="Unsupported format"):
            format_output(data, "xml")  # 不支持的格式

    def test_empty_data_handling(self) -> None:
        """测试空数据的处理."""
        # 空文件列表
        data = FileListData(path="/", total=0, files=[])
        result = format_output(data, OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed["total"] == 0
        assert parsed["files"] == []

        # 空重复文件
        data = DuplicateData(total_groups=0, total_size_saved=0, groups=[])
        result = format_output(data, OutputFormat.CSV)
        lines = result.strip().split("\n")
        assert len(lines) == 1  # 只有标题行

    # 在 tests/test_formatter.py 中添加以下测试用例

    def test_file_list_with_modified_time(self) -> None:
        """测试包含修改时间的文件列表格式化."""
        # 准备测试数据
        data = FileListData(
            path="/test/path",
            total=1,
            files=[
                {
                    "name": "file1.txt",
                    "size": 1024,
                    "type": "file",
                    "modified": "2025-05-29 10:30:00",
                }
            ],
        )

        # 测试JSON格式包含所有字段
        result = format_output(data, OutputFormat.JSON)
        parsed = json.loads(result)
        assert "modified" in parsed["files"][0]

    def test_format_size_in_plain_output(self) -> None:
        """测试纯文本输出中的文件大小格式化."""
        # 准备测试数据，包含一个辅助函数格式化大小
        from simple_tools.utils.formatter import format_size_for_display

        # 测试不同大小的格式化
        assert format_size_for_display(0) == "0 B"
        assert format_size_for_display(1023) == "1023 B"
        assert format_size_for_display(1024) == "1.0 KB"
        assert format_size_for_display(1048576) == "1.0 MB"
        assert format_size_for_display(1073741824) == "1.0 GB"

    def test_special_characters_in_filenames(self) -> None:
        """测试文件名中的特殊字符处理."""
        # 准备包含特殊字符的测试数据
        data = FileListData(
            path="/test/path",
            total=1,
            files=[
                {"name": "file with spaces.txt", "size": 1024, "type": "file"},
                {"name": "文件名.txt", "size": 2048, "type": "file"},
                {"name": "file,with,comma.csv", "size": 512, "type": "file"},
            ],
        )

        # 测试CSV格式正确处理特殊字符
        result = format_output(data, OutputFormat.CSV)
        assert "file with spaces.txt" in result
        assert "文件名.txt" in result
        assert '"file,with,comma.csv"' in result  # CSV应该用引号包裹含逗号的字段

    # 在 tests/test_formatter.py 中补充错误处理测试

    def test_format_with_none_data(self) -> None:
        """测试处理空数据."""
        data = FileListData(path="/", total=0, files=[])

        # 所有格式都应该能处理空数据
        for format_type in [OutputFormat.PLAIN, OutputFormat.JSON, OutputFormat.CSV]:
            result = format_output(data, format_type)
            assert result is not None

    def test_large_file_size_formatting(self) -> None:
        """测试大文件大小格式化."""
        from simple_tools.utils.formatter import format_size_for_display

        # 测试TB级别
        assert format_size_for_display(1099511627776) == "1.0 TB"
        assert format_size_for_display(2199023255552) == "2.0 TB"

    def test_csv_escaping(self) -> None:
        """测试CSV中的特殊字符转义."""
        data = FileListData(
            path="/test",
            total=1,
            files=[{"name": 'file"with"quotes.txt', "size": 1024, "type": "file"}],
        )

        result = format_output(data, OutputFormat.CSV)
        # CSV应该正确转义引号
        assert (
            '"file""with""quotes.txt"' in result or "'file\"with\"quotes.txt'" in result
        )

    # 在 tests/test_formatter.py 中添加

    def test_format_plain_with_large_numbers(self) -> None:
        """测试纯文本格式处理大数字."""
        data = DuplicateData(
            total_groups=1,
            total_size_saved=1099511627776,  # 1TB
            groups=[
                {
                    "hash": "abc",
                    "size": 1099511627776,
                    "count": 2,
                    "files": ["/file1", "/file2"],
                }
            ],
        )

        result = format_output(data, OutputFormat.PLAIN)
        assert "1.0 TB" in result

    def test_invalid_format_type(self) -> None:
        """测试无效的格式类型."""
        data = FileListData(path="/", total=0, files=[])

        # 测试完全无效的格式
        with pytest.raises(ValueError):
            format_output(data, "invalid_format")

        # 测试None
        with pytest.raises(ValueError):
            format_output(data, None)

    def test_csv_with_no_files(self) -> None:
        """测试CSV格式处理空文件列表."""
        data = FileListData(path="/empty", total=0, files=[])
        result = format_output(data, OutputFormat.CSV)

        # 应该只有标题行
        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert lines[0] == "name,size,type"
