"""文件整理工具模块."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import click
import logfire
from pydantic import BaseModel, Field

from simple_tools._typing import argument, command, option, pass_context

from ..utils.errors import (
    BatchErrorCollector,
    ErrorContext,
    ToolError,
    handle_errors,
)
from ..utils.progress import ProgressTracker
from ..utils.smart_interactive import smart_confirm_sync


class OrganizeConfig(BaseModel):
    """文件整理配置."""

    path: str = Field(".", description="要整理的目录路径")
    mode: str = Field("type", description="整理模式：type/date/mixed")
    recursive: bool = Field(False, description="是否递归处理子目录")
    dry_run: bool = Field(True, description="预览模式")
    skip_confirm: bool = Field(False, description="跳过确认")


class FileCategory(BaseModel):
    """文件类别定义."""

    name: str = Field(..., description="类别名称")
    icon: str = Field(..., description="显示图标")
    extensions: list[str] = Field(..., description="文件扩展名列表")
    folder_name: str = Field(..., description="目标文件夹名称")


class OrganizeItem(BaseModel):
    """整理项."""

    source_path: Path = Field(..., description="原始文件路径")
    target_path: Path = Field(..., description="目标文件路径")
    category: str = Field(..., description="文件类别")
    status: str = Field(
        "pending", description="处理状态：pending/success/failed/skipped"
    )
    error: Optional[str] = Field(None, description="错误信息")


class OrganizeResult(BaseModel):
    """整理结果."""

    total: int = Field(0, description="总文件数")
    moved: int = Field(0, description="成功移动数")
    skipped: int = Field(0, description="跳过数")
    failed: int = Field(0, description="失败数")
    items: list[OrganizeItem] = Field(default_factory=list, description="处理项列表")


class FileOrganizerTool:
    """文件整理工具类."""

    # 预定义文件类别
    CATEGORIES = [
        FileCategory(
            name="图片",
            icon="📷",
            folder_name="图片",
            extensions=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
        ),
        FileCategory(
            name="文档",
            icon="📄",
            folder_name="文档",
            extensions=[
                ".doc",
                ".docx",
                ".pdf",
                ".txt",
                ".odt",
                ".xls",
                ".xlsx",
                ".ppt",
                ".pptx",
            ],
        ),
        FileCategory(
            name="视频",
            icon="🎬",
            folder_name="视频",
            extensions=[".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
        ),
        FileCategory(
            name="音频",
            icon="🎵",
            folder_name="音频",
            extensions=[".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"],
        ),
        FileCategory(
            name="压缩包",
            icon="📦",
            folder_name="压缩包",
            extensions=[".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        ),
        FileCategory(
            name="代码",
            icon="💻",
            folder_name="代码",
            extensions=[".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".go"],
        ),
        FileCategory(
            name="其他",
            icon="📁",
            folder_name="其他",
            extensions=[],  # 兜底类别，无扩展名限制
        ),
    ]

    def __init__(self, config: OrganizeConfig):
        """初始化文件整理工具."""
        self.config = config
        self.base_path = Path(config.path)
        logfire.info(
            "初始化文件整理工具",
            attributes={
                "path": config.path,
                "mode": config.mode,
                "recursive": config.recursive,
            },
        )

    @handle_errors("扫描文件")
    def scan_files(self) -> list[Path]:
        """扫描需要整理的文件."""
        if not self.base_path.exists():
            raise ToolError(
                f"扫描路径不存在: {self.config.path}",
                error_code="FILE_NOT_FOUND",
                context=ErrorContext(
                    operation="扫描文件", file_path=str(self.base_path)
                ),
                suggestions=[
                    "检查路径拼写是否正确",
                    "确认目录是否存在",
                    "使用绝对路径重试",
                ],
            )
        if not self.base_path.is_dir():
            raise ToolError(
                f"路径不是目录: {self.config.path}",
                error_code="NOT_A_DIRECTORY",
                context=ErrorContext(
                    operation="扫描文件", file_path=str(self.base_path)
                ),
                suggestions=["指定一个目录路径", "使用 --file 参数处理单个文件"],
            )
        try:
            files = []
            if self.config.recursive:
                files = list(self.base_path.rglob("*"))
            else:
                files = list(self.base_path.iterdir())
            return [f for f in files if f.is_file() and not f.name.startswith(".")]
        except PermissionError:
            raise ToolError(
                f"无权限访问目录: {self.config.path}",
                error_code="PERMISSION_DENIED",
                context=ErrorContext(
                    operation="扫描文件", file_path=str(self.base_path)
                ),
                suggestions=[
                    "检查目录权限设置",
                    "尝试使用管理员权限运行",
                    "选择有权限访问的目录",
                ],
            )

    def classify_file(self, file_path: Path) -> FileCategory:
        """根据扩展名对文件进行分类."""
        ext = file_path.suffix.lower()
        for category in self.CATEGORIES[:-1]:
            if ext in category.extensions:
                return category
        return self.CATEGORIES[-1]

    def generate_target_path(self, file_path: Path, category: FileCategory) -> Path:
        """生成目标路径."""
        if self.config.mode == "type":
            return self.base_path / category.folder_name / file_path.name
        elif self.config.mode == "date":
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return (
                self.base_path / str(mtime.year) / f"{mtime.month:02d}" / file_path.name
            )
        else:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return (
                self.base_path
                / category.folder_name
                / str(mtime.year)
                / f"{mtime.month:02d}"
                / file_path.name
            )

    def create_organize_plan(self) -> list[OrganizeItem]:
        """创建整理计划."""
        files = self.scan_files()
        items = []
        for file_path in files:
            category = self.classify_file(file_path)
            target_path = self.generate_target_path(file_path, category)
            status = "pending"
            error = None
            if target_path.exists():
                status = "skipped"
                error = "目标文件已存在"
            items.append(
                OrganizeItem(
                    source_path=file_path,
                    target_path=target_path,
                    category=category.name,
                    status=status,
                    error=error,
                )
            )
        return items

    def _move_file(
        self, item: OrganizeItem, result: OrganizeResult, collector: BatchErrorCollector
    ) -> None:
        """单文件移动逻辑，拆分以降低复杂度."""
        try:
            item.target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item.source_path), str(item.target_path))
            item.status = "success"
            result.moved += 1
            collector.record_success()
        except PermissionError as e:
            item.status = "failed"
            item.error = "没有权限移动文件"
            result.failed += 1
            collector.record_error(item.source_path, e)
        except OSError as e:
            if e.errno == 28:  # ENOSPC
                item.status = "failed"
                item.error = "磁盘空间不足"
                result.failed += 1
                collector.record_error(
                    item.source_path,
                    ToolError("磁盘空间不足", error_code="DISK_FULL", original_error=e),
                )
            else:
                item.status = "failed"
                item.error = str(e)
                result.failed += 1
                collector.record_error(item.source_path, e)
        except Exception as e:
            item.status = "failed"
            item.error = str(e)
            result.failed += 1
            collector.record_error(item.source_path, e)

    def execute_organize(self, items: list[OrganizeItem]) -> OrganizeResult:
        """执行文件整理."""
        result = OrganizeResult(total=len(items))
        collector = BatchErrorCollector("文件整理")

        def process_item(item: OrganizeItem) -> None:
            if item.status == "skipped":
                result.skipped += 1
                return
            self._move_file(item, result, collector)

        if len(items) > 50:
            with ProgressTracker(total=len(items), description="整理文件") as progress:
                for item in items:
                    process_item(item)
                    progress.update(1)
        else:
            for item in items:
                process_item(item)

        if collector.has_errors():
            click.echo("\n" + collector.format_summary())

        result.items = items
        return result

    def print_scan_summary(
        self,
        path: str,
        mode: str,
        items: list[OrganizeItem],
        category_stats: dict[str, list[Any]],
    ) -> None:
        """打印扫描和整理计划摘要，避免 organize_cmd 过于复杂。."""
        click.echo(f"\n扫描目录: {os.path.abspath(path)}")
        click.echo(f"整理模式: {_get_mode_desc(mode)}")
        click.echo(f"找到 {len(items)} 个文件需要整理\n")

        click.echo("整理计划：")
        for category_name, category_items in category_stats.items():
            icon = "📁"
            for cat in self.CATEGORIES:
                if cat.name == category_name:
                    icon = cat.icon
                    break

            pending_count = len([i for i in category_items if i.status == "pending"])
            if pending_count > 0:
                target_dir = category_items[0].target_path.parent
                rel_target = os.path.relpath(target_dir, path)
                click.echo(
                    f"{icon} {category_name} ({pending_count}个文件) → "
                    f"{rel_target}/"
                )

                for item in category_items[:3]:
                    if item.status == "pending":
                        click.echo(f"  • {item.source_path.name}")

                if len(category_items) > 3:
                    click.echo("  ...")

        skipped_count = len([i for i in items if i.status == "skipped"])
        if skipped_count > 0:
            click.echo(f"\n⚠️  将跳过 {skipped_count} 个文件（目标位置已存在同名文件）")

    def print_organize_result(self, result: OrganizeResult) -> None:
        """打印整理结果."""
        click.echo("\n整理完成：")
        click.echo(f"  成功移动: {result.moved} 个文件")
        if result.skipped > 0:
            click.echo(f"  跳过: {result.skipped} 个文件")
        if result.failed > 0:
            click.echo(f"  失败: {result.failed} 个文件")

        logfire.info(
            "文件整理完成",
            attributes={
                "moved": result.moved,
                "skipped": result.skipped,
                "failed": result.failed,
            },
        )


def _get_mode_desc(mode: str) -> str:
    """获取模式描述."""
    mode_map = {"type": "按文件类型", "date": "按修改日期", "mixed": "按类型和日期"}
    return mode_map.get(mode, mode)


def _get_format_type(ctx: click.Context, format: Optional[str]) -> str:
    """获取输出格式类型."""
    if format:
        return format

    config = ctx.obj.get("config") if ctx.obj else None
    if config and hasattr(config, "format"):
        return str(getattr(config, "format", "plain"))

    return "plain"


def _prepare_organize_config(
    ctx: click.Context,
    path: str,
    mode: Optional[str],
    recursive: Optional[bool],
    dry_run: Optional[bool],
    execute: bool,
    yes: bool,
) -> OrganizeConfig:
    """准备文件整理配置."""
    config = ctx.obj.get("config") if ctx.obj else None
    if config and hasattr(config, "organize") and config.organize:
        if mode is None:
            mode = config.organize.mode
        if recursive is None:
            recursive = config.organize.recursive
        if dry_run is None and not execute:
            dry_run = config.organize.dry_run
    if mode is None:
        mode = "type"
    if recursive is None:
        recursive = False
    if dry_run is None and not execute:
        dry_run = True
    if execute:
        dry_run = False
    return OrganizeConfig(
        path=path,
        mode=mode,
        recursive=recursive,
        dry_run=dry_run,
        skip_confirm=yes,
    )


def _process_organize_plan(
    organizer: FileOrganizerTool,
    items: list[OrganizeItem],
    dry_run: bool,
    skip_confirm: bool,
    format_type: str = "plain",
) -> Optional[OrganizeResult]:
    """处理整理计划."""
    pending_count = len([i for i in items if i.status == "pending"])

    if dry_run and pending_count > 0:
        click.echo("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        click.echo(f"将移动 {pending_count} 个文件")
        click.echo("已展示整理计划（预览模式，未实际移动文件）。")
        return None

    if pending_count > 0:
        if not dry_run and not skip_confirm:
            files_to_move = [
                str(item.source_path) for item in items if item.status == "pending"
            ]
            preview_changes = {}
            shown = 0
            for item in items:
                if item.status == "pending":
                    rel_source = os.path.relpath(item.source_path, organizer.base_path)
                    rel_target = os.path.relpath(item.target_path, organizer.base_path)
                    preview_changes[rel_source] = rel_target
                    shown += 1
                    if shown >= 5:
                        break
            mode_desc = _get_mode_desc(organizer.config.mode)
            estimated_impact = "high" if pending_count > 50 else "medium"
            if not smart_confirm_sync(
                operation=f"整理 {pending_count} 个文件（{mode_desc}）",
                files_affected=files_to_move,
                estimated_impact=estimated_impact,
                preview_changes=preview_changes,
            ):
                click.echo("操作已取消")
                return None

        click.echo("\n正在整理文件...")
        return organizer.execute_organize(items)
    else:
        click.echo("没有文件需要移动。")
        return None


def _handle_format_output(
    items: list[OrganizeItem],
    result: Optional[OrganizeResult],
    organize_config: OrganizeConfig,
    format_type: str,
) -> None:
    """处理格式化输出."""
    from ..utils.formatter import OrganizeData, format_output

    organize_results = []
    for item in items:
        organize_results.append(
            {
                "source_path": str(item.source_path),
                "target_path": str(item.target_path),
                "category": item.category,
                "status": item.status,
                "error": item.error,
            }
        )

    data = OrganizeData(
        total=len(items),
        moved=result.moved if result and not organize_config.dry_run else 0,
        skipped=(
            result.skipped
            if result and not organize_config.dry_run
            else len([i for i in items if i.status == "skipped"])
        ),
        failed=(result.failed if result and not organize_config.dry_run else 0),
        results=organize_results,
    )

    output = format_output(data, format_type)
    click.echo(output)


def _record_organize_history(
    items: list[OrganizeItem],
    result: Optional[OrganizeResult],
    organize_config: OrganizeConfig,
    category_stats: dict[str, list[Any]],
    path: str,
) -> None:
    """记录操作历史."""
    from ..utils.smart_interactive import operation_history

    if organize_config.dry_run:
        pending_count = len([i for i in items if i.status == "pending"])
        skipped_count = len([i for i in items if i.status == "skipped"])
        category_counts = {}
        for cat_name, cat_items in category_stats.items():
            category_counts[cat_name] = len(
                [i for i in cat_items if i.status == "pending"]
            )
        operation_history.add(
            "organize",
            {
                "path": path,
                "mode": organize_config.mode,
                "recursive": organize_config.recursive,
                "dry_run": True,
            },
            {
                "total_files": len(items),
                "planned_moves": pending_count,
                "planned_skips": skipped_count,
                "status": "preview",
                "categories": category_counts,
            },
        )
    elif result:
        category_counts = {}
        for cat_name, cat_items in category_stats.items():
            category_counts[cat_name] = len(
                [i for i in cat_items if i.status == "success"]
            )
        operation_history.add(
            "organize",
            {
                "path": path,
                "mode": organize_config.mode,
                "recursive": organize_config.recursive,
                "dry_run": False,
            },
            {
                "total_files": result.total,
                "moved": result.moved,
                "skipped": result.skipped,
                "failed": result.failed,
                "status": "executed",
                "categories": category_counts,
            },
        )


@command()
@argument("path", type=click.Path(), default=".")
@option(
    "--mode",
    type=click.Choice(["type", "date", "mixed"], case_sensitive=False),
    default=None,
    help="整理模式：type(按类型)、date(按日期)、mixed(混合)",
)
@option("-r", "--recursive", is_flag=True, default=None, help="递归处理子目录")
@option("-d", "--dry-run", is_flag=True, default=None, help="预览模式")
@option("--execute", is_flag=True, help="执行模式（跳过预览）")
@option("-y", "--yes", is_flag=True, help="跳过确认提示")
@option(
    "--format",
    type=click.Choice(["plain", "json", "csv"], case_sensitive=False),
    default=None,
    help="输出格式（plain/json/csv）",
)
@pass_context
def organize_cmd(
    ctx: click.Context,
    path: str,
    mode: Optional[str],
    recursive: Optional[bool],
    dry_run: Optional[bool],
    execute: bool,
    yes: bool,
    format: Optional[str],
) -> None:
    """自动整理文件到相应目录."""
    try:
        organize_config = _prepare_organize_config(
            ctx, path, mode, recursive, dry_run, execute, yes
        )

        with logfire.span(
            "file_organize",
            attributes={
                "path": path,
                "mode": organize_config.mode,
                "recursive": organize_config.recursive,
            },
        ):
            organizer = FileOrganizerTool(organize_config)
            items = organizer.create_organize_plan()

            if not items:
                click.echo("没有找到需要整理的文件。")
                return

            format_type = _get_format_type(ctx, format)

            category_stats: dict[str, list[Any]] = {}
            for item in items:
                if item.category not in category_stats:
                    category_stats[item.category] = []
                category_stats[item.category].append(item)

            if format_type == "plain":
                organizer.print_scan_summary(
                    path, organize_config.mode, items, category_stats
                )

            result = _process_organize_plan(
                organizer,
                items,
                organize_config.dry_run,
                organize_config.skip_confirm,
                format_type,
            )

            if format_type != "plain":
                _handle_format_output(items, result, organize_config, format_type)
            else:
                if result:
                    organizer.print_organize_result(result)

            _record_organize_history(
                items, result, organize_config, category_stats, path
            )

    except ToolError as e:
        click.echo(e.format_message(), err=True)
        raise click.ClickException(str(e))
    except Exception as e:
        logfire.error(f"文件整理失败: {str(e)}")
        error = ToolError(
            "文件整理失败",
            error_code="GENERAL_ERROR",
            context=ErrorContext(operation="文件整理", details={"error": str(e)}),
            original_error=e,
            suggestions=[
                "检查输入参数是否正确",
                "确认目录权限设置",
                "查看详细错误日志",
            ],
        )
        click.echo(error.format_message(), err=True)
        raise click.ClickException(str(e))
