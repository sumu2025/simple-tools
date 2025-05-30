"""文件处理工具 - 提供文件列表、查找等功能."""

import os
from datetime import datetime
from typing import Any

import click
import logfire

from simple_tools._typing import argument, command, option, pass_context  # 新增

from ..utils.formatter import FileListData, OutputFormat, format_output


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

        try:
            # 检查目录是否存在
            if not os.path.exists(directory):
                logfire.error(f"目录不存在: {directory}")
                raise click.ClickException(f"错误：目录 '{directory}' 不存在")

            # 检查是否为目录
            if not os.path.isdir(directory):
                logfire.error(f"路径不是目录: {directory}")
                raise click.ClickException(f"错误：'{directory}' 不是一个目录")

            # 获取目录内容
            items = os.listdir(directory)

            # 过滤隐藏文件
            if not show_hidden:
                items = [item for item in items if not item.startswith(".")]

            # 排序：目录在前，按名称排序
            items.sort(
                key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower())
            )

            # 收集文件信息
            for item in items:
                item_path = os.path.join(directory, item)
                is_dir = os.path.isdir(item_path)

                info = {"name": item, "is_dir": is_dir, "path": item_path}

                if show_details and not is_dir:
                    size = os.path.getsize(item_path)
                    info["size"] = size
                    info["size_formatted"] = format_size(size)
                    modified_time: float = float(os.path.getmtime(item_path))
                    info["modified"] = modified_time
                    info["modified_formatted"] = format_time(modified_time)

                items_info.append(info)

            logfire.info(
                f"列出目录内容成功: {directory}",
                attributes={"item_count": len(items_info)},
            )

        except PermissionError:
            logfire.error(f"权限错误: {directory}")
            raise click.ClickException(f"错误：没有权限访问目录 '{directory}'")
        except Exception as e:
            logfire.error(f"列出目录内容失败: {str(e)}")
            raise click.ClickException(f"错误：{str(e)}")

        return items_info


# 修改 list_cmd 函数，添加 format 参数，此部分为新增，未删除原内容
@command()
@argument("path", type=click.Path(exists=True), default=".")
@option("-a", "--all", is_flag=True, help="显示隐藏文件（以.开头的文件）")
@option("-l", "--long", is_flag=True, help="显示详细信息（文件大小、修改时间）")
@option(
    "--format",
    type=click.Choice(["plain", "json", "csv"], case_sensitive=False),
    default="plain",
    help="输出格式（plain/json/csv）",
)
@pass_context
def list_cmd(ctx: click.Context, path: str, all: bool, long: bool, format: str) -> None:
    """列出指定目录下的文件和文件夹.

    PATH: 要列出的目录路径（默认为当前目录）
    """
    ctx.obj["config"]

    try:
        items = list_files(path, show_hidden=all, show_details=long)

        # 根据格式选择输出方式
        if format != "plain":
            # 构建格式化数据
            files_data = []
            for item in items:
                file_info = {
                    "name": item["name"],
                    "type": "directory" if item["is_dir"] else "file",
                    "size": item.get("size", 0),
                }
                if long and "modified_formatted" in item:
                    file_info["modified"] = item["modified_formatted"]
                files_data.append(file_info)

            # 创建数据模型
            data = FileListData(
                path=os.path.abspath(path), total=len(items), files=files_data
            )

            # 格式化输出
            output = format_output(data, OutputFormat(format))
            click.echo(output)
        else:
            # 保持原有的纯文本输出方式
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
                    size_info = f" ({item['size_formatted']})" if long else ""

                if long and not item["is_dir"]:
                    # E501修复：分多行拼接
                    click.echo(
                        f"{type_indicator:<6} {item['name']:<30} "
                        f"{size_info:<10} {item['modified_formatted']}"
                    )
                else:
                    click.echo(f"{type_indicator} {item['name']}{size_info}")

            # 输出统计信息
            click.echo(f"\n总计: {len(items)} 个项目")

    except click.ClickException as e:
        click.echo(str(e), err=True)
