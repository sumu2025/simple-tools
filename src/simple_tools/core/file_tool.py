"""文件工具模块 - 集成现代化错误处理系统."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import click
import logfire

from simple_tools._typing import argument, command, option, pass_context

from ..utils.errors import ErrorContext, ToolError, format_friendly_error, handle_errors
from ..utils.formatter import FileListData, format_output
from ..utils.progress import ProgressTracker  # 新增进度显示支持


def format_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的文件大小格式.

    参数：size_bytes - 文件大小（字节）
    返回：格式化后的大小字符串.
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def format_time(timestamp: float) -> str:
    """将Unix时间戳转换为可读的时间格式.

    参数：timestamp - Unix时间戳（秒）
    返回：格式化后的时间字符串.
    """
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def _scan_directory_with_progress(
    path: str, show_hidden: bool = False
) -> list[dict[str, Any]]:
    """扫描目录并在大量文件时显示进度."""
    path_obj = Path(path)

    # 默认排除的目录（不递归扫描，所以只在当前层级检查）
    excluded_dirs = {
        ".venv",
        "venv",
        "env",  # 虚拟环境
        ".git",
        ".svn",
        ".hg",  # 版本控制
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",  # 缓存
        "node_modules",
        "dist",
        "build",  # 构建目录
        ".idea",
        ".vscode",  # IDE配置
        "site-packages",  # Python包目录
    }

    # 先快速统计文件数量（仅用于判断是否需要进度条）
    try:
        all_items = list(path_obj.iterdir())
        if not show_hidden:
            all_items = [item for item in all_items if not item.name.startswith(".")]

        # 过滤掉排除的目录
        all_items = [item for item in all_items if item.name not in excluded_dirs]

        # 如果文件数量超过1000个，显示进度条
        if len(all_items) > 1000:
            items_info = []
            with ProgressTracker(
                total=len(all_items), description="扫描文件"
            ) as progress:
                for item in all_items:
                    is_dir = item.is_dir()
                    info = {"name": item.name, "is_dir": is_dir, "path": str(item)}
                    items_info.append(info)
                    progress.update(1)
            return items_info
        else:
            # 文件数量较少，直接处理
            items_info = []
            for item in all_items:
                is_dir = item.is_dir()
                info = {"name": item.name, "is_dir": is_dir, "path": str(item)}
                items_info.append(info)
            return items_info
    except PermissionError as e:
        # 如果无法访问目录，抛出 ToolError
        raise ToolError(
            f"没有权限访问目录 '{path}'",
            error_code="PERMISSION_DENIED",
            context=ErrorContext(operation="列出目录内容", file_path=path),
            original_error=e,
        )
    except OSError as e:
        # 其他系统错误
        raise ToolError(
            f"访问目录失败 '{path}'",
            error_code="OPERATION_FAILED",
            context=ErrorContext(operation="列出目录内容", file_path=path),
            original_error=e,
        )


@handle_errors("列出目录内容")
def list_files(
    directory: str, show_hidden: bool = False, show_details: bool = False
) -> list[dict[str, Any]]:
    """列出指定目录下的文件和文件夹.

    参数：
        directory - 目标目录路径字符串
        show_hidden - 布尔值，是否显示隐藏文件（以.开头的文件）
        show_details - 布尔值，是否显示详细信息（大小、修改时间）
    返回：
        items_info - 包含文件信息的字典列表.
    """
    with logfire.span(
        "list_files",
        attributes={
            "directory": directory,
            "show_hidden": show_hidden,
            "show_details": show_details,
        },
    ):
        items_info = []

        # 检查目录是否存在
        if not os.path.exists(directory):
            raise ToolError(
                f"目录 '{directory}' 不存在",
                error_code="DIRECTORY_NOT_FOUND",
                context=ErrorContext(operation="列出目录内容", file_path=directory),
            )

        # 检查是否为目录
        if not os.path.isdir(directory):
            raise ToolError(
                f"路径 '{directory}' 不是一个目录",
                error_code="NOT_A_DIRECTORY",
                context=ErrorContext(operation="列出目录内容", file_path=directory),
            )

        # 默认排除的目录
        excluded_dirs = {
            ".venv",
            "venv",
            "env",  # 虚拟环境
            ".git",
            ".svn",
            ".hg",  # 版本控制
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",  # 缓存
            "node_modules",
            "dist",
            "build",  # 构建目录
            ".idea",
            ".vscode",  # IDE配置
            "site-packages",  # Python包目录
        }

        # 使用带进度显示的目录扫描
        if not show_details:
            items_info = _scan_directory_with_progress(directory, show_hidden)
        else:
            # 获取目录内容
            try:
                items = os.listdir(directory)
            except PermissionError as e:
                raise ToolError(
                    f"没有权限访问目录 '{directory}'",
                    error_code="PERMISSION_DENIED",
                    context=ErrorContext(operation="列出目录内容", file_path=directory),
                    original_error=e,
                )

            # 过滤隐藏文件
            if not show_hidden:
                items = [item for item in items if not item.startswith(".")]

            # 过滤排除的目录
            items = [item for item in items if item not in excluded_dirs]

            # 排序：目录在前，按名称排序
            items.sort(
                key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower())
            )

            # 收集文件信息（带详细信息时可能较慢，但通常文件数不会太多）
            for item in items:
                item_path = os.path.join(directory, item)
                is_dir = os.path.isdir(item_path)

                info = {"name": item, "is_dir": is_dir, "path": item_path}

                if show_details and not is_dir:
                    try:
                        size = os.path.getsize(item_path)
                        info["size"] = size
                        info["size_formatted"] = format_size(size)
                        modified_time: float = float(os.path.getmtime(item_path))
                        info["modified"] = modified_time
                        info["modified_formatted"] = format_time(modified_time)
                    except (OSError, PermissionError) as e:
                        # 对于无法访问的文件，记录错误但继续处理其他文件
                        logfire.warning(
                            f"无法获取文件详情: {item_path}, 错误: {str(e)}"
                        )
                        info["size"] = 0
                        info["size_formatted"] = "未知"
                        info["modified_formatted"] = "未知"

                items_info.append(info)

        # 排序：目录在前，按名称排序
        items_info.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        logfire.info(
            f"列出目录内容成功: {directory}",
            attributes={"item_count": len(items_info)},
        )

        return items_info


def _prepare_list_config(
    ctx: click.Context,
    all: Optional[bool],
    long: Optional[bool],
    format: Optional[str],
) -> tuple[bool, bool, str]:
    """准备列表命令的配置参数.

    从命令行参数和配置文件中获取配置，并处理默认值。
    """
    # 获取配置
    config = ctx.obj.get("config")

    # 调试输出
    logfire.debug(f"list_cmd 参数值 - all: {all}, long: {long}, format: {format}")

    # 应用配置文件的默认值（命令行参数优先）
    if config:
        # 只有当用户没有指定参数时，才使用配置文件的值
        if all is None and hasattr(config, "list") and hasattr(config.list, "show_all"):
            all = config.list.show_all
        if long is None and hasattr(config, "list") and hasattr(config.list, "long"):
            long = config.list.long
        if format is None and hasattr(config, "format") and config.format:
            format = config.format

    # 设置最终的默认值
    if all is None:
        all = False
    if long is None:
        long = False
    if format is None:
        format = "plain"

    logfire.debug(f"list_cmd 最终值 - all: {all}, long: {long}, format: {format}")

    return all, long, format


def _format_list_output(
    items: list[dict[str, Any]], path: str, format_type: str
) -> None:
    """根据指定格式输出文件列表.

    处理格式化输出（JSON/CSV）或纯文本输出。
    """
    if format_type != "plain":
        # 构建格式化数据
        files_data = []
        for item in items:
            file_info = {
                "name": item["name"],
                "type": "directory" if item["is_dir"] else "file",
                "size": item.get("size", 0),
            }
            if "modified_formatted" in item:
                file_info["modified"] = item["modified_formatted"]
            files_data.append(file_info)

        # 创建数据模型
        data = FileListData(
            path=os.path.abspath(path), total=len(items), files=files_data
        )

        # 格式化输出
        output = format_output(data, format_type)
        click.echo(output)
    else:
        _print_plain_text_list(items, path)


def _print_plain_text_list(items: list[dict[str, Any]], path: str) -> None:
    """以纯文本格式打印文件列表."""
    click.echo(f"\n目录: {os.path.abspath(path)}")
    click.echo("-" * 60)

    # 如果目录为空
    if not items:
        click.echo("目录为空")
        return

    # 输出文件列表
    for item in items:
        if item["is_dir"]:
            type_indicator = "[目录]"
            size_info = ""
        else:
            type_indicator = "[文件]"
            size_info = (
                f" ({item['size_formatted']})" if "size_formatted" in item else ""
            )

        if "modified_formatted" in item and not item["is_dir"]:
            # E501修复：分多行拼接
            click.echo(
                f"{type_indicator:<6} {item['name']:<30} "
                f"{size_info:<10} {item['modified_formatted']}"
            )
        else:
            click.echo(f"{type_indicator} {item['name']}{size_info}")

    # 输出统计信息
    click.echo(f"\n总计: {len(items)} 个项目")


@command()
@argument("path", type=click.Path(exists=True), default=".")
@option("-a", "--all/--no-all", default=None, help="显示隐藏文件（以.开头的文件）")
@option(
    "-l", "--long/--no-long", default=None, help="显示详细信息（文件大小、修改时间）"
)
@option(
    "--format",
    type=click.Choice(["plain", "json", "csv"], case_sensitive=False),
    default=None,
    help="输出格式（plain/json/csv）",
)
@pass_context
def list_cmd(
    ctx: click.Context,
    path: str,
    all: Optional[bool],
    long: Optional[bool],
    format: Optional[str],
) -> None:
    """列出指定目录下的文件和文件夹.

    PATH: 要列出的目录路径（默认为当前目录）
    """
    try:
        # 准备配置参数
        show_hidden, show_details, output_format = _prepare_list_config(
            ctx, all, long, format
        )

        # 获取文件列表
        items = list_files(path, show_hidden=show_hidden, show_details=show_details)

        # 格式化输出
        _format_list_output(items, path, output_format)

        # 记录到操作历史
        from ..utils.smart_interactive import operation_history

        operation_history.add(
            "list",
            {
                "path": path,
                "all": show_hidden,
                "long": show_details,
                "format": output_format,
            },
            {"files_count": len(items)},
        )

    except ToolError as e:
        # 使用友好的错误格式化
        error_msg = format_friendly_error(e)
        click.echo(error_msg, err=True)
    except click.ClickException as e:
        click.echo(str(e), err=True)
