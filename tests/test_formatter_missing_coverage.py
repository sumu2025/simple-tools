# tests/test_formatter_missing_coverage.py
"""补充formatter模块缺失的测试覆盖."""
import json

import pytest

from simple_tools._typing import OutputFormat
from simple_tools.utils.formatter import (
    DuplicateData,
    FileListData,
    Formatter,
    OrganizeData,
    RenameData,
    ReplaceData,
    format_output,
)


class TestFormatterMissingCoverage:
    """补充formatter缺失测试覆盖的测试类."""

    def test_rename_data_json_format(self) -> None:
        """测试重命名数据的JSON格式输出."""
        data = RenameData(
            total=2,
            results=[
                {
                    "old_path": "/old/file1.txt",
                    "new_path": "/new/file1_renamed.txt",
                    "status": "success",
                    "error": None,
                },
                {
                    "old_path": "/old/file2.txt",
                    "new_path": "/new/file2_renamed.txt",
                    "status": "failed",
                    "error": "File already exists",
                },
            ],
        )

        result = format_output(data, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed["total"] == 2
        assert len(parsed["rename_results"]) == 2
        assert parsed["rename_results"][0]["status"] == "success"
        assert parsed["rename_results"][1]["error"] == "File already exists"

    def test_rename_data_csv_format(self) -> None:
        """测试重命名数据的CSV格式输出."""
        data = RenameData(
            total=1,
            results=[
                {
                    "old_path": "/old/file.txt",
                    "new_path": "/new/file_renamed.txt",
                    "status": "success",
                    "error": None,
                }
            ],
        )

        result = format_output(data, OutputFormat.CSV)
        lines = result.strip().split("\n")

        assert len(lines) == 2  # 头部 + 1行数据
        assert "old_path,new_path,status,error" in lines[0]
        assert "/old/file.txt" in lines[1]
        assert "success" in lines[1]

    def test_rename_data_plain_format(self) -> None:
        """测试重命名数据的Plain格式输出."""
        data = RenameData(
            total=2,
            results=[
                {
                    "old_path": "/path/file1.txt",
                    "new_path": "/path/renamed1.txt",
                    "status": "success",
                    "error": None,
                },
                {
                    "old_path": "/path/file2.txt",
                    "new_path": "/path/renamed2.txt",
                    "status": "failed",
                    "error": "Permission denied",
                },
            ],
        )

        result = format_output(data, OutputFormat.PLAIN)

        assert "✓ file1.txt → renamed1.txt" in result
        assert "✗ file2.txt - Permission denied" in result
        assert "重命名完成：成功 1 个，失败 1 个" in result

    def test_replace_data_json_format(self) -> None:
        """测试文本替换数据的JSON格式输出."""
        data = ReplaceData(
            total=2,
            results=[
                {
                    "file_path": "/path/file1.txt",
                    "match_count": 3,
                    "replaced": True,
                    "error": None,
                },
                {
                    "file_path": "/path/file2.txt",
                    "match_count": 0,
                    "replaced": False,
                    "error": "File not found",
                },
            ],
        )

        result = format_output(data, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed["total"] == 2
        assert len(parsed["replace_results"]) == 2
        assert parsed["replace_results"][0]["match_count"] == 3
        assert parsed["replace_results"][1]["error"] == "File not found"

    def test_replace_data_csv_format(self) -> None:
        """测试文本替换数据的CSV格式输出."""
        data = ReplaceData(
            total=1,
            results=[
                {
                    "file_path": "/path/test.txt",
                    "match_count": 5,
                    "replaced": True,
                    "error": None,
                }
            ],
        )

        result = format_output(data, OutputFormat.CSV)
        lines = result.strip().split("\n")

        assert len(lines) == 2
        assert "file_path,match_count,replaced,error" in lines[0]
        assert "/path/test.txt" in lines[1]
        assert "5" in lines[1]

    def test_replace_data_plain_format(self) -> None:
        """测试文本替换数据的Plain格式输出."""
        data = ReplaceData(
            total=2,
            results=[
                {
                    "file_path": "/path/file1.txt",
                    "match_count": 2,
                    "replaced": True,
                    "error": None,
                },
                {
                    "file_path": "/path/file2.txt",
                    "match_count": 0,
                    "replaced": False,
                    "error": "Permission denied",
                },
            ],
        )

        result = format_output(data, OutputFormat.PLAIN)

        assert "✓ file1.txt - 成功替换 2 处" in result
        assert "✗ file2.txt - Permission denied" in result
        assert "替换完成：处理文件 1 个，总替换数 2 处" in result

    def test_organize_data_json_format(self) -> None:
        """测试文件整理数据的JSON格式输出."""
        data = OrganizeData(
            total=2,
            results=[
                {
                    "source_path": "/downloads/photo.jpg",
                    "target_path": "/downloads/图片/photo.jpg",
                    "category": "图片",
                    "status": "success",
                },
                {
                    "source_path": "/downloads/document.pdf",
                    "target_path": "/downloads/文档/document.pdf",
                    "category": "文档",
                    "status": "failed",
                },
            ],
        )

        result = format_output(data, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed["total"] == 2
        assert len(parsed["organize_results"]) == 2
        assert parsed["organize_results"][0]["category"] == "图片"
        assert parsed["organize_results"][1]["status"] == "failed"

    def test_organize_data_csv_format(self) -> None:
        """测试文件整理数据的CSV格式输出."""
        data = OrganizeData(
            total=1,
            results=[
                {
                    "source_path": "/downloads/file.txt",
                    "target_path": "/downloads/文档/file.txt",
                    "category": "文档",
                    "status": "success",
                }
            ],
        )

        result = format_output(data, OutputFormat.CSV)
        lines = result.strip().split("\n")

        assert len(lines) == 2
        assert "source_path,target_path,category,status" in lines[0]
        assert "/downloads/file.txt" in lines[1]
        assert "文档" in lines[1]

    def test_organize_data_plain_format(self) -> None:
        """测试文件整理数据的Plain格式输出."""
        data = OrganizeData(
            total=3,
            results=[
                {
                    "source_path": "/downloads/photo1.jpg",
                    "target_path": "/downloads/图片/photo1.jpg",
                    "category": "图片",
                    "status": "success",
                },
                {
                    "source_path": "/downloads/photo2.jpg",
                    "target_path": "/downloads/图片/photo2.jpg",
                    "category": "图片",
                    "status": "success",
                },
                {
                    "source_path": "/downloads/doc.pdf",
                    "target_path": "/downloads/文档/doc.pdf",
                    "category": "文档",
                    "status": "failed",
                },
            ],
        )

        result = format_output(data, OutputFormat.PLAIN)

        assert "📁 图片 (2 个文件):" in result
        assert "✓ photo1.jpg" in result
        assert "✓ photo2.jpg" in result
        assert "📁 文档 (1 个文件):" in result
        assert "✗ doc.pdf" in result
        assert "整理完成：成功移动 2 个文件，失败 1 个" in result

    def test_formatter_invalid_format_type(self) -> None:
        """测试无效格式类型抛出异常."""
        with pytest.raises(ValueError, match="Unsupported format"):
            Formatter("invalid_format")

    def test_formatter_non_outputformat_type(self) -> None:
        """测试非OutputFormat类型的处理."""
        # 测试OutputFormatType类型（如果存在）
        formatter = Formatter("json")
        assert formatter.format_type == "json"

        # 测试其他类型转换为字符串
        from simple_tools._typing import OutputFormatType

        if hasattr(OutputFormatType, "JSON"):
            formatter = Formatter(OutputFormatType.JSON)
            assert formatter.format_type == "json"

    def test_file_list_plain_format_zero_size_files(self) -> None:
        """测试Plain格式处理零大小文件."""
        data = FileListData(
            path="/test",
            total=1,
            files=[{"name": "empty.txt", "size": 0, "type": "file"}],
        )

        result = format_output(data, OutputFormat.PLAIN)

        # 测试零大小文件的格式化（覆盖行257）
        assert "empty.txt [file]" in result
        # 不应该包含文件大小信息
        assert "(0 B)" not in result

    def test_duplicates_plain_format_empty_groups(self) -> None:
        """测试Plain格式处理空重复文件组."""
        data = DuplicateData(
            total_groups=0,
            total_size_saved=0,
            groups=[],
        )

        result = format_output(data, OutputFormat.PLAIN)

        # 测试空组的处理（覆盖行264）
        assert result == "未发现重复文件"

    def test_format_output_none_data_validation(self) -> None:
        """测试format_output函数的数据验证."""
        # 测试None数据 - 使用有效的数据类型替代
        data = FileListData(path="/", total=0, files=[])
        with pytest.raises(ValueError, match="Format type cannot be None"):
            format_output(data, None)

    def test_format_output_unsupported_data_type(self) -> None:
        """测试format_output函数处理不支持的数据类型."""
        # 创建一个不支持的数据类型 - 使用有效的数据类型替代
        data = FileListData(path="/", total=0, files=[])

        with pytest.raises(ValueError, match="Unsupported format"):
            format_output(data, "xml")

    def test_empty_rename_results(self) -> None:
        """测试空重命名结果的处理."""
        data = RenameData(total=0, results=[])
        result = format_output(data, OutputFormat.PLAIN)

        assert result == "无文件需要重命名"

    def test_empty_replace_results(self) -> None:
        """测试空替换结果的处理."""
        data = ReplaceData(total=0, results=[])
        result = format_output(data, OutputFormat.PLAIN)

        assert result == "无文件需要替换"

    def test_empty_organize_results(self) -> None:
        """测试空整理结果的处理."""
        data = OrganizeData(total=0, results=[])
        result = format_output(data, OutputFormat.PLAIN)

        assert result == "无文件需要整理"

    def test_organize_plain_format_many_files_truncation(self) -> None:
        """测试文件整理Plain格式的文件数量截断."""
        # 创建超过5个文件的数据来测试截断功能
        results = []
        for i in range(7):  # 创建7个文件
            results.append(
                {
                    "source_path": f"/downloads/file{i}.txt",
                    "target_path": f"/downloads/文档/file{i}.txt",
                    "category": "文档",
                    "status": "success",
                }
            )

        data = OrganizeData(total=7, results=results)
        result = format_output(data, OutputFormat.PLAIN)

        # 应该显示"还有X个文件"的提示
        assert "... 还有 2 个文件" in result
        assert "📁 文档 (7 个文件):" in result

    def test_formatter_string_format_validation(self) -> None:
        """测试字符串格式验证."""
        # 测试有效格式
        for valid_format in ["plain", "json", "csv"]:
            formatter = Formatter(valid_format)
            assert formatter.format_type == valid_format

        # 测试无效字符串格式
        with pytest.raises(ValueError, match="Unsupported format"):
            format_output(FileListData(path="/", total=0, files=[]), "xml")
