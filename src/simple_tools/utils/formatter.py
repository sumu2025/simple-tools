# src/simple_tools/utils/formatter.py
"""输出格式化工具模块."""
import csv
import json
from enum import Enum
from io import StringIO
from typing import Any, Union

from pydantic import BaseModel


class OutputFormat(str, Enum):
    """输出格式枚举."""

    PLAIN = "plain"
    JSON = "json"
    CSV = "csv"


class FileListData(BaseModel):
    """文件列表数据模型."""

    path: str
    total: int
    files: list[dict[str, Any]]


class DuplicateData(BaseModel):
    """重复文件数据模型."""

    total_groups: int
    total_size_saved: int
    groups: list[dict[str, Any]]


def format_output(
    data: Union[FileListData, DuplicateData], format_type: Union[OutputFormat, str]
) -> str:
    """统一的输出格式化函数.

    Args:
        data: 要格式化的数据
        format_type: 输出格式类型

    Returns:
        格式化后的字符串

    """
    # 检查 format_type 是否为 None
    if format_type is None:
        raise ValueError("Format type cannot be None")

    # 确保format_type是OutputFormat类型
    if isinstance(format_type, str):
        try:
            format_type = OutputFormat(format_type)
        except ValueError:
            raise ValueError(f"Unsupported format: {format_type}")

    if format_type == OutputFormat.JSON:
        return _format_json(data)
    elif format_type == OutputFormat.CSV:
        return _format_csv(data)
    else:  # PLAIN
        return _format_plain(data)


def _format_json(data: Union[FileListData, DuplicateData]) -> str:
    """格式化为JSON."""
    return json.dumps(data.model_dump(), indent=2, ensure_ascii=False)


def _format_csv(data: Union[FileListData, DuplicateData]) -> str:
    """格式化为CSV."""
    output = StringIO()

    if isinstance(data, FileListData):
        # 文件列表CSV格式
        writer = csv.DictWriter(output, fieldnames=["name", "size", "type"])
        writer.writeheader()
        if data.files:
            writer.writerows(data.files)

    elif isinstance(data, DuplicateData):
        # 重复文件CSV格式
        if data.groups:
            # 计算最大文件数
            max_files = (
                max(len(group["files"]) for group in data.groups) if data.groups else 0
            )

            # 构建字段名
            fieldnames = ["hash", "size", "count"]
            for i in range(1, max_files + 1):
                fieldnames.append(f"file{i}")

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            # 写入数据
            for group in data.groups:
                row = {
                    "hash": group["hash"],
                    "size": group["size"],
                    "count": group["count"],
                }
                # 添加文件路径
                for i, file_path in enumerate(group["files"], 1):
                    row[f"file{i}"] = file_path
                writer.writerow(row)
        else:
            # 空数据时只写标题
            writer = csv.DictWriter(
                output, fieldnames=["hash", "size", "count", "file1"]
            )
            writer.writeheader()

    return output.getvalue()


# 在 src/simple_tools/utils/formatter.py 中添加


def format_size_for_display(size_bytes: int) -> str:
    """将字节数转换为人类可读的格式.

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串，如 "1.5 MB"

    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:  # 字节
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


# 修改 _format_plain 函数，使用格式化的文件大小
def _format_plain(data: Union[FileListData, DuplicateData]) -> str:
    """格式化为纯文本（默认格式）."""
    lines = []

    if isinstance(data, FileListData):
        # 文件列表纯文本格式
        for file_info in data.files:
            size_str = format_size_for_display(file_info["size"])
            lines.append(f"{file_info['name']} ({size_str})")

    elif isinstance(data, DuplicateData):
        # 重复文件纯文本格式
        for i, group in enumerate(data.groups, 1):
            size_str = format_size_for_display(group["size"])
            lines.append(f"Group {i}: {group['count']} files, {size_str} each")
            for file_path in group["files"]:
                lines.append(f"  - {file_path}")

    return "\n".join(lines)
