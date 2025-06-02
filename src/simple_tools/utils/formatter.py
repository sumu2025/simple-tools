"""输出格式化模块.

提供统一的输出格式化接口，支持多种输出格式：
- plain: 默认的人类友好格式
- json: 结构化JSON格式
- csv: 表格CSV格式
"""

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, Union

import logfire
from pydantic import BaseModel, Field

from .._typing import OutputFormat, OutputFormatType


# 数据模型定义
class FileListData(BaseModel):
    """文件列表数据模型."""

    path: str = Field(..., description="目录路径")
    total: int = Field(..., description="文件总数")
    files: list[dict[str, Any]] = Field(..., description="文件信息列表")


class DuplicateData(BaseModel):
    """重复文件数据模型."""

    total_groups: int = Field(..., description="重复文件组数")
    total_size_saved: int = Field(..., description="可节省的总空间")
    groups: list[dict[str, Any]] = Field(..., description="重复文件组列表")


class RenameData(BaseModel):
    """重命名数据模型."""

    total: int = Field(..., description="操作文件总数")
    results: list[dict[str, Any]] = Field(..., description="重命名结果列表")


class ReplaceData(BaseModel):
    """替换数据模型."""

    total: int = Field(..., description="操作文件总数")
    results: list[dict[str, Any]] = Field(..., description="替换结果列表")


class OrganizeData(BaseModel):
    """整理数据模型."""

    total: int = Field(..., description="操作文件总数")
    results: list[dict[str, Any]] = Field(..., description="整理结果列表")


def format_size_for_display(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式.

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的大小字符串

    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


class Formatter:
    """统一的输出格式化器."""

    def __init__(
        self, format_type: Union[OutputFormat, OutputFormatType, str] = "plain"
    ):
        """初始化格式化器.

        Args:
            format_type: 输出格式类型

        """
        # 标准化格式类型
        if isinstance(format_type, OutputFormat):
            self.format_type = format_type.value
        elif isinstance(format_type, str):
            self.format_type = format_type
        else:
            self.format_type = str(format_type)

        # 验证格式类型
        valid_formats = ["plain", "json", "csv"]
        if self.format_type not in valid_formats:
            valid_list = ", ".join(valid_formats)
            raise ValueError(
                f"Unsupported format: {self.format_type}. "
                f"Valid formats: {valid_list}"
            )

        logfire.debug(f"初始化格式化器: {self.format_type}")

    def format_file_list(self, files: list[dict[str, Any]], path: str) -> str:
        """格式化文件列表输出."""
        if self.format_type == "json":
            return self._format_file_list_json(files, path)
        elif self.format_type == "csv":
            return self._format_file_list_csv(files)
        else:  # plain
            return self._format_file_list_plain(files)

    def format_duplicates(self, data: DuplicateData) -> str:
        """格式化重复文件输出."""
        if self.format_type == "json":
            return self._format_duplicates_json(data)
        elif self.format_type == "csv":
            return self._format_duplicates_csv(data.groups)
        else:  # plain
            return self._format_duplicates_plain(data.groups)

    def format_rename_result(self, results: list[dict[str, Any]]) -> str:
        """格式化重命名结果输出."""
        if self.format_type == "json":
            return self._format_rename_json(results)
        elif self.format_type == "csv":
            return self._format_rename_csv(results)
        else:  # plain
            return self._format_rename_plain(results)

    def format_replace_result(self, results: list[dict[str, Any]]) -> str:
        """格式化文本替换结果输出."""
        if self.format_type == "json":
            return self._format_replace_json(results)
        elif self.format_type == "csv":
            return self._format_replace_csv(results)
        else:  # plain
            return self._format_replace_plain(results)

    def format_organize_result(self, results: list[dict[str, Any]]) -> str:
        """格式化文件整理结果输出."""
        if self.format_type == "json":
            return self._format_organize_json(results)
        elif self.format_type == "csv":
            return self._format_organize_csv(results)
        else:  # plain
            return self._format_organize_plain(results)

    # JSON格式化方法
    def _format_file_list_json(self, files: list[dict[str, Any]], path: str) -> str:
        """JSON格式的文件列表."""
        output = {"path": path, "total": len(files), "files": files}
        return json.dumps(output, ensure_ascii=False, indent=2)

    def _format_duplicates_json(self, data: DuplicateData) -> str:
        """JSON格式的重复文件."""
        return json.dumps(
            {
                "groups": data.groups,
                "total_groups": data.total_groups,
                "total_size_saved": data.total_size_saved,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _format_rename_json(self, results: list[dict[str, Any]]) -> str:
        """JSON格式的重命名结果."""
        return json.dumps(
            {"rename_results": results, "total": len(results)},
            ensure_ascii=False,
            indent=2,
        )

    def _format_replace_json(self, results: list[dict[str, Any]]) -> str:
        """JSON格式的替换结果."""
        return json.dumps(
            {"replace_results": results, "total": len(results)},
            ensure_ascii=False,
            indent=2,
        )

    def _format_organize_json(self, results: list[dict[str, Any]]) -> str:
        """JSON格式的整理结果."""
        return json.dumps(
            {"organize_results": results, "total": len(results)},
            ensure_ascii=False,
            indent=2,
        )

    # CSV格式化方法
    def _format_file_list_csv(self, files: list[dict[str, Any]]) -> str:
        """CSV格式的文件列表."""
        if not files:
            return "name,type,size,modified\n"

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["name", "type", "size", "modified"])
        writer.writeheader()
        writer.writerows(files)
        return output.getvalue()

    def _format_duplicates_csv(self, groups: list[dict[str, Any]]) -> str:
        """CSV格式的重复文件."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["hash", "size", "count", "files"])

        for group in groups:
            files_str = "|".join(str(f) for f in group.get("files", []))
            writer.writerow(
                [
                    group.get("hash", ""),
                    group.get("size", 0),
                    group.get("count", 0),
                    files_str,
                ]
            )

        return output.getvalue()

    def _format_rename_csv(self, results: list[dict[str, Any]]) -> str:
        """CSV格式的重命名结果."""
        output = StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["old_path", "new_path", "status", "error"]
        )
        writer.writeheader()
        writer.writerows(results)
        return output.getvalue()

    def _format_replace_csv(self, results: list[dict[str, Any]]) -> str:
        """CSV格式的替换结果."""
        output = StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["file_path", "match_count", "replaced", "error"]
        )
        writer.writeheader()
        writer.writerows(results)
        return output.getvalue()

    def _format_organize_csv(self, results: list[dict[str, Any]]) -> str:
        """CSV格式的整理结果."""
        output = StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["source_path", "target_path", "category", "status"]
        )
        writer.writeheader()
        writer.writerows(results)
        return output.getvalue()

    # Plain格式化方法（默认人类友好格式）
    def _format_file_list_plain(self, files: list[dict[str, Any]]) -> str:
        """Plain格式的文件列表."""
        if not files:
            return "目录为空"

        lines = []
        for file in files:
            name = file.get("name", "")
            size = file.get("size", 0)
            file_type = file.get("type", "")

            if size > 0:
                size_str = format_size_for_display(size)
                lines.append(f"{name} ({size_str}) [{file_type}]")
            else:
                lines.append(f"{name} [{file_type}]")

        return "\n".join(lines)

    def _format_duplicates_plain(self, groups: list[dict[str, Any]]) -> str:
        """Plain格式的重复文件."""
        if not groups:
            return "未发现重复文件"

        lines = []
        total_waste = 0

        for i, group in enumerate(groups, 1):
            size = group.get("size", 0)
            count = group.get("count", 0)
            files = group.get("files", [])

            waste = size * (count - 1)
            total_waste += waste

            size_display = format_size_for_display(size)
            waste_display = format_size_for_display(waste)
            lines.append(
                f"【第 {i} 组】{count} 个文件, 每个 {size_display}, "
                f"可节省 {waste_display}"
            )
            for file in files:
                lines.append(f"  • {file}")
            lines.append("")  # 空行分隔

        total_waste_display = format_size_for_display(total_waste)
        lines.append(
            f"总计：{len(groups)} 组重复文件，" f"可节省 {total_waste_display} 空间"
        )
        return "\n".join(lines)

    def _format_rename_plain(self, results: list[dict[str, Any]]) -> str:
        """Plain格式的重命名结果."""
        if not results:
            return "无文件需要重命名"

        lines = []
        success_count = sum(1 for r in results if r.get("status") == "success")
        failed_count = len(results) - success_count

        for result in results:
            old_path = result.get("old_path", "")
            new_path = result.get("new_path", "")
            status = result.get("status", "")
            error = result.get("error", "")

            if status == "success":
                lines.append(f"  ✓ {Path(old_path).name} → {Path(new_path).name}")
            else:
                lines.append(f"  ✗ {Path(old_path).name} - {error}")

        lines.append(f"\n重命名完成：成功 {success_count} 个，失败 {failed_count} 个")
        return "\n".join(lines)

    def _format_replace_plain(self, results: list[dict[str, Any]]) -> str:
        """Plain格式的替换结果."""
        if not results:
            return "无文件需要替换"

        lines = []
        total_replacements = sum(r.get("match_count", 0) for r in results)
        success_count = sum(1 for r in results if r.get("replaced", False))

        for result in results:
            file_path = result.get("file_path", "")
            match_count = result.get("match_count", 0)
            replaced = result.get("replaced", False)
            error = result.get("error", "")

            if replaced and match_count > 0:
                lines.append(f"  ✓ {Path(file_path).name} - 成功替换 {match_count} 处")
            elif error:
                lines.append(f"  ✗ {Path(file_path).name} - {error}")

        lines.append(
            f"\n替换完成：处理文件 {success_count} 个，总替换数 {total_replacements} 处"
        )
        return "\n".join(lines)

    def _format_organize_plain(self, results: list[dict[str, Any]]) -> str:
        """Plain格式的整理结果."""
        if not results:
            return "无文件需要整理"

        lines = []
        success_count = sum(1 for r in results if r.get("status") == "success")
        failed_count = len(results) - success_count

        # 按类别分组显示
        categories: dict[str, list[dict[str, Any]]] = {}
        for result in results:
            category = result.get("category", "其他")
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        for category, items in categories.items():
            lines.append(f"\n📁 {category} ({len(items)} 个文件):")
            for item in items[:5]:  # 只显示前5个
                source = Path(item.get("source_path", "")).name
                status = item.get("status", "")
                if status == "success":
                    lines.append(f"  ✓ {source}")
                else:
                    lines.append(f"  ✗ {source}")

            if len(items) > 5:
                lines.append(f"  ... 还有 {len(items) - 5} 个文件")

        lines.append(
            f"\n整理完成：成功移动 {success_count} 个文件，失败 {failed_count} 个"
        )
        return "\n".join(lines)


# 统一的格式化输出函数
def format_output(
    data: Union[FileListData, DuplicateData, RenameData, ReplaceData, OrganizeData],
    format_type: Union[OutputFormat, OutputFormatType, str, None],
) -> str:
    """统一的格式化输出函数."""
    # 验证参数
    if data is None:
        raise ValueError("Data cannot be None")

    if format_type is None:
        raise ValueError("Format type cannot be None")

    # 验证格式类型
    if isinstance(format_type, str) and format_type not in ["plain", "json", "csv"]:
        raise ValueError(f"Unsupported format: {format_type}")

    formatter = Formatter(format_type)

    if isinstance(data, FileListData):
        return formatter.format_file_list(data.files, data.path)
    elif isinstance(data, DuplicateData):
        return formatter.format_duplicates(data)
    elif isinstance(data, RenameData):
        return formatter.format_rename_result(data.results)
    elif isinstance(data, ReplaceData):
        return formatter.format_replace_result(data.results)
    elif isinstance(data, OrganizeData):
        return formatter.format_organize_result(data.results)
    else:
        raise ValueError(f"Unsupported data type: {type(data)}")


def create_formatter(
    format_type: Union[OutputFormat, OutputFormatType, str],
) -> Formatter:
    """创建格式化器实例."""
    return Formatter(format_type)
