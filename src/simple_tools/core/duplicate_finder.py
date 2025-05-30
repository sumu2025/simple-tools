"""重复文件检测工具 - 智能查找目录中的重复文件."""

import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

import click
import logfire
from pydantic import BaseModel, Field

from simple_tools._typing import argument, command, option, pass_context

from ..utils.formatter import DuplicateData, OutputFormat, format_output
from ..utils.progress import process_with_progress


class DuplicateConfig(BaseModel):
    """重复文件检测配置."""

    path: str = Field(..., description="扫描路径")
    recursive: bool = Field(True, description="是否递归扫描子目录")
    min_size: int = Field(1, description="最小文件大小（字节）")
    extensions: Optional[list[str]] = Field(None, description="指定文件扩展名")


class FileInfo(BaseModel):
    """文件信息."""

    path: Path = Field(..., description="文件路径")
    size: int = Field(..., description="文件大小（字节）")
    hash: Optional[str] = Field(None, description="文件MD5哈希值")


class DuplicateGroup(BaseModel):
    """重复文件组."""

    hash: str = Field(..., description="文件MD5哈希值")
    size: int = Field(..., description="文件大小（字节）")
    count: int = Field(..., description="重复文件数量")
    files: list[Path] = Field(..., description="重复文件路径列表")
    potential_save: int = Field(..., description="可节省空间（字节）保留一个文件")


class DuplicateFinder:
    """重复文件检测器."""

    def __init__(self, config: DuplicateConfig):
        """初始化重复文件检测器.

        参数：config - 检测配置对象
        """
        self.config = config
        logfire.info("初始化重复文件检测器", attributes={"config": config.model_dump()})

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件的MD5哈希值（分块读取，避免大文件内存问题）.

        参数：file_path - 文件路径对象
        返回：MD5哈希值字符串
        """
        hash_md5 = hashlib.md5()

        try:
            with open(file_path, "rb") as f:
                # 每次读取8KB，避免大文件占用过多内存
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logfire.error(
                f"计算文件哈希失败: {file_path}", attributes={"error": str(e)}
            )
            raise

    def _should_include_file(self, file_path: Path) -> bool:
        """判断文件是否应该包含在检测范围内.

        参数：file_path - 文件路径对象
        返回：布尔值，True表示应该包含
        """
        # 检查文件大小是否满足最小要求
        try:
            file_size = file_path.stat().st_size
            if file_size < self.config.min_size:
                return False
        except OSError:
            return False

        # 检查文件扩展名是否在指定列表中
        if self.config.extensions:
            file_ext = file_path.suffix.lower()
            return file_ext in [ext.lower() for ext in self.config.extensions]

        return True

    def _scan_files(self) -> list[FileInfo]:
        """扫描目录获取所有符合条件的文件信息.

        返回：FileInfo对象列表
        """
        with logfire.span("scan_files", attributes={"path": self.config.path}):
            files = []
            scan_path = Path(self.config.path)

            try:
                # 根据配置选择扫描方式
                if self.config.recursive:
                    pattern = "**/*"
                else:
                    pattern = "*"

                # 扫描文件
                for file_path in scan_path.glob(pattern):
                    # 只处理文件，跳过目录
                    if not file_path.is_file():
                        continue

                    # 检查是否应该包含此文件
                    if not self._should_include_file(file_path):
                        continue

                    # 获取文件大小
                    file_size = file_path.stat().st_size

                    # 创建文件信息对象
                    files.append(FileInfo(path=file_path, size=file_size))

                logfire.info(f"扫描完成，找到 {len(files)} 个文件")
                return files

            except Exception as e:
                logfire.error(f"扫描文件失败: {str(e)}")
                raise

    def find_duplicates(self) -> list[DuplicateGroup]:
        """查找重复文件.

        返回：DuplicateGroup对象列表，每个组包含重复的文件
        """
        with logfire.span("find_duplicates"):
            logfire.info("开始重复文件检测")

            # 第一步：扫描所有文件
            all_files = self._scan_files()
            if not all_files:
                logfire.info("没有找到符合条件的文件")
                return []

            # 第二步：按文件大小分组
            size_groups = self._group_files_by_size(all_files)
            # 过滤掉只有一个文件的大小组
            potential_duplicates = {
                size: files for size, files in size_groups.items() if len(files) > 1
            }
            logfire.info(
                f"按大小分组后，{len(potential_duplicates)} 个大小组可能包含重复文件"
            )

            # 第三步：组装哈希任务
            all_files_to_hash = self._collect_files_to_hash(potential_duplicates)
            logfire.info(f"需要计算 {len(all_files_to_hash)} 个文件的哈希值")

            # 第四步：批量计算哈希并分组
            size_hash_groups = self._group_files_by_hash(all_files_to_hash)

            # 第五步：组装最终重复组
            duplicate_groups = self._assemble_duplicate_groups(size_hash_groups)

            # 按可节省空间排序（从大到小）
            duplicate_groups.sort(key=lambda x: x.potential_save, reverse=True)
            logfire.info(f"检测完成，发现 {len(duplicate_groups)} 组重复文件")
            return duplicate_groups

    def _group_files_by_size(
        self, all_files: list["FileInfo"]
    ) -> dict[int, list["FileInfo"]]:
        """按文件大小分组."""
        groups = defaultdict(list)
        for file_info in all_files:
            groups[file_info.size].append(file_info)
        return groups

    def _collect_files_to_hash(
        self, potential_duplicates: dict[int, list["FileInfo"]]
    ) -> list[tuple[int, "FileInfo"]]:
        """组装需要计算哈希的文件列表."""
        all_files_to_hash = []
        for file_size, files in potential_duplicates.items():
            all_files_to_hash.extend([(file_size, file_info) for file_info in files])
        return all_files_to_hash

    def _group_files_by_hash(
        self, all_files_to_hash: list[tuple[int, FileInfo]]
    ) -> dict[int, dict[str, list[FileInfo]]]:
        """批量计算哈希并按大小和哈希分组."""

        def calculate_hash_for_file(
            file_data: tuple[int, FileInfo],
        ) -> Optional[tuple[int, FileInfo, str]]:
            file_size, file_info = file_data
            try:
                file_hash = self._calculate_file_hash(file_info.path)
                file_info.hash = file_hash
                return (file_size, file_info, file_hash)
            except Exception as e:
                logfire.warning(f"跳过文件 {file_info.path}: {str(e)}")
                return None

        size_hash_groups: dict[int, dict[str, list[FileInfo]]] = defaultdict(
            lambda: defaultdict(list)
        )
        results = process_with_progress(
            all_files_to_hash,
            calculate_hash_for_file,
            label="计算文件哈希值",
            threshold=100,
        )
        for result in results:
            if result is not None:
                file_size, file_info, file_hash = result
                size_hash_groups[file_size][file_hash].append(file_info)
        # 转为常规 dict 返回，保证类型一致
        return {size: dict(hash_group) for size, hash_group in size_hash_groups.items()}

    def _assemble_duplicate_groups(
        self, size_hash_groups: dict[int, dict[str, list["FileInfo"]]]
    ) -> list["DuplicateGroup"]:
        """组装最终的重复文件组."""
        duplicate_groups = []
        for file_size, hash_groups in size_hash_groups.items():
            for file_hash, duplicate_files in hash_groups.items():
                if len(duplicate_files) > 1:
                    potential_save = file_size * (len(duplicate_files) - 1)
                    duplicate_group = DuplicateGroup(
                        hash=file_hash,
                        size=file_size,
                        count=len(duplicate_files),
                        files=[f.path for f in duplicate_files],
                        potential_save=potential_save,
                    )
                    duplicate_groups.append(duplicate_group)
        return duplicate_groups


def format_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的文件大小格式.

    复用file_tool.py中的函数逻辑
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


def display_duplicate_results(
    duplicate_groups: list[DuplicateGroup],
    scan_path: str,
    total_files: int,
    recursive: bool,
    show_commands: bool = False,
) -> None:
    """友好展示重复文件检测结果.

    参数：
        duplicate_groups - 重复文件组列表
        scan_path - 扫描路径
        total_files - 扫描的文件总数
        recursive - 是否递归扫描
        show_commands - 是否显示删除建议命令
    """
    # 输出扫描信息
    click.echo(f"扫描目录: {scan_path}")
    click.echo(f"扫描模式: {'递归扫描' if recursive else '仅顶层目录'}")
    click.echo(f"文件总数: {total_files:,} 个")
    click.echo("━" * 60)

    # 如果没有重复文件
    if not duplicate_groups:
        click.echo("🎉 未发现重复文件！")
        return

    # 显示重复文件组
    click.echo(f"发现 {len(duplicate_groups)} 组重复文件：\n")

    total_duplicates = 0
    total_save_space = 0

    for index, group in enumerate(duplicate_groups, 1):
        total_duplicates += group.count
        total_save_space += group.potential_save

        # 显示组标题
        click.echo(
            f"【第 {index} 组】{group.count} 个文件, "
            f"每个 {format_size(group.size)}, "
            f"可节省 {format_size(group.potential_save)}"
        )

        # 显示文件列表
        for file_path in group.files:
            click.echo(f"  • {file_path}")

        # 如果需要显示删除命令建议
        if show_commands and len(group.files) > 1:
            click.echo(f"  💡 建议保留: {group.files[0]}")
            click.echo("  🗑️  可删除命令:")
            for file_path in group.files[1:]:
                click.echo(f"     rm '{file_path}'")

        click.echo()  # 空行分隔

    # 显示总结统计
    click.echo("━" * 60)
    click.echo(
        f"总计：{total_duplicates} 个重复文件，"
        f"可节省 {format_size(total_save_space)} 空间"
    )

    if show_commands:
        click.echo("\n⚠️  警告：删除文件前请确认重要性，建议先备份！")


# 修改 duplicates_cmd 函数，添加 format 参数
@command()
@argument("path", type=click.Path(exists=True), default=".")
@option(
    "-r", "--recursive", is_flag=True, default=True, help="递归扫描子目录（默认启用）"
)
@option("-n", "--no-recursive", is_flag=True, help="仅扫描顶层目录，不递归")
@option("-s", "--min-size", type=int, default=1, help="最小文件大小（字节），默认1")
@option(
    "-e",
    "--extension",
    multiple=True,
    help="指定文件扩展名（可多次使用），如：-e .jpg -e .png",
)
@option("--show-commands", is_flag=True, help="显示删除重复文件的建议命令")
@option(
    "--format",
    type=click.Choice(["plain", "json", "csv"], case_sensitive=False),
    default="plain",
    help="输出格式（plain/json/csv）",
)
@pass_context
def duplicates_cmd(
    ctx: click.Context,
    path: str,
    recursive: bool,
    no_recursive: bool,
    min_size: int,
    extension: tuple[str, ...],
    show_commands: bool,
    format: str,
) -> None:
    """查找指定目录中的重复文件.

    PATH: 要扫描的目录路径（默认为当前目录）

    示例用法：
      tools duplicates .                    # 扫描当前目录
      tools duplicates ~/Downloads -n       # 只扫描Downloads顶层
      tools duplicates . -s 1048576        # 只查找大于1MB的文件
      tools duplicates . -e .jpg -e .png   # 只查找图片文件
      tools duplicates . --show-commands   # 显示删除建议
      tools duplicates . --format json     # JSON格式输出
    """
    # 处理递归选项冲突
    if no_recursive:
        recursive = False

    # 转换扩展名列表
    extensions = list(extension) if extension else None

    try:
        # 创建配置对象
        config = DuplicateConfig(
            path=path, recursive=recursive, min_size=min_size, extensions=extensions
        )

        # 创建检测器并执行检测
        finder = DuplicateFinder(config)

        # 显示开始信息（仅在plain格式时显示）
        if format == "plain":
            click.echo("🔍 开始扫描重复文件...")

        # 执行检测
        duplicate_groups = finder.find_duplicates()

        # 计算扫描的总文件数（用于统计显示）
        all_files = finder._scan_files()
        total_files = len(all_files)

        # 根据格式选择输出方式
        if format != "plain":
            # 计算总的节省空间
            total_save_space = sum(group.potential_save for group in duplicate_groups)

            # 构建格式化数据
            groups_data = []
            for group in duplicate_groups:
                groups_data.append(
                    {
                        "hash": group.hash,
                        "size": group.size,
                        "count": group.count,
                        "files": [str(f) for f in group.files],
                    }
                )

            # 创建数据模型
            data = DuplicateData(
                total_groups=len(duplicate_groups),
                total_size_saved=total_save_space,
                groups=groups_data,
            )

            # 格式化输出
            output = format_output(data, OutputFormat(format))
            click.echo(output)
        else:
            # 保持原有的纯文本输出方式
            display_duplicate_results(
                duplicate_groups=duplicate_groups,
                scan_path=os.path.abspath(path),
                total_files=total_files,
                recursive=recursive,
                show_commands=show_commands,
            )

    except click.ClickException:
        # Click异常直接传播
        raise
    except Exception as e:
        # 其他异常转换为Click异常
        logfire.error(f"重复文件检测失败: {str(e)}")
        raise click.ClickException(f"错误：{str(e)}")
