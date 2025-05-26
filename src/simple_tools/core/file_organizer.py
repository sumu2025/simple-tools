"""
文件整理工具 - 按类型和日期自动整理文件
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import click
import logfire
from pydantic import BaseModel, Field
from ..config import get_config


class OrganizeConfig(BaseModel):
    """文件整理配置"""
    path: str = Field(".", description="要整理的目录路径")
    mode: str = Field("type", description="整理模式：type/date/mixed")
    recursive: bool = Field(False, description="是否递归处理子目录")
    dry_run: bool = Field(True, description="预览模式")
    skip_confirm: bool = Field(False, description="跳过确认")


class FileCategory(BaseModel):
    """文件类别定义"""
    name: str = Field(..., description="类别名称")
    icon: str = Field(..., description="显示图标")
    extensions: List[str] = Field(..., description="文件扩展名列表")
    folder_name: str = Field(..., description="目标文件夹名称")


class OrganizeItem(BaseModel):
    """整理项"""
    source_path: Path = Field(..., description="原始文件路径")
    target_path: Path = Field(..., description="目标文件路径")
    category: str = Field(..., description="文件类别")
    status: str = Field("pending", description="处理状态：pending/success/failed/skipped")
    error: Optional[str] = Field(None, description="错误信息")


class OrganizeResult(BaseModel):
    """整理结果"""
    total: int = Field(0, description="总文件数")
    moved: int = Field(0, description="成功移动数")
    skipped: int = Field(0, description="跳过数")
    failed: int = Field(0, description="失败数")
    items: List[OrganizeItem] = Field(default_factory=list, description="处理项列表")


class FileOrganizerTool:
    """文件整理工具类"""

    # 预定义文件类别
    CATEGORIES = [
        FileCategory(
            name="图片", icon="📷", folder_name="图片",
            extensions=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"]
        ),
        FileCategory(
            name="文档", icon="📄", folder_name="文档",
            extensions=[".doc", ".docx", ".pdf", ".txt", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"]
        ),
        FileCategory(
            name="视频", icon="🎬", folder_name="视频",
            extensions=[".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"]
        ),
        FileCategory(
            name="音频", icon="🎵", folder_name="音频",
            extensions=[".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"]
        ),
        FileCategory(
            name="压缩包", icon="📦", folder_name="压缩包",
            extensions=[".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"]
        ),
        FileCategory(
            name="代码", icon="💻", folder_name="代码",
            extensions=[".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".go"]
        ),
        FileCategory(
            name="其他", icon="📁", folder_name="其他",
            extensions=[]  # 兜底类别，无扩展名限制
        )
    ]

    def __init__(self, config: OrganizeConfig):
        self.config = config
        self.base_path = Path(config.path)
        logfire.info("初始化文件整理工具", attributes={
            "path": config.path,
            "mode": config.mode,
            "recursive": config.recursive
        })

    def scan_files(self) -> List[Path]:
        """扫描需要整理的文件"""
        files = []

        if self.config.recursive:
            files = list(self.base_path.rglob("*"))
        else:
            files = list(self.base_path.iterdir())

        # 只处理普通文件，跳过目录和隐藏文件
        return [f for f in files if f.is_file() and not f.name.startswith('.')]

    def classify_file(self, file_path: Path) -> FileCategory:
        """根据扩展名对文件进行分类"""
        ext = file_path.suffix.lower()

        for category in self.CATEGORIES[:-1]:  # 排除"其他"类别
            if ext in category.extensions:
                return category

        # 默认归类到"其他"
        return self.CATEGORIES[-1]

    def generate_target_path(self, file_path: Path, category: FileCategory) -> Path:
        """生成目标路径"""
        if self.config.mode == "type":
            # 按类型分类：base_path/类别名/文件名
            return self.base_path / category.folder_name / file_path.name
        elif self.config.mode == "date":
            # 按日期分类：base_path/年/月/文件名
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return self.base_path / str(mtime.year) / f"{mtime.month:02d}" / file_path.name
        else:  # mixed模式
            # 混合分类：base_path/类别名/年/月/文件名
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return self.base_path / category.folder_name / str(mtime.year) / f"{mtime.month:02d}" / file_path.name

    def create_organize_plan(self) -> List[OrganizeItem]:
        """创建整理计划"""
        files = self.scan_files()
        items = []

        for file_path in files:
            category = self.classify_file(file_path)
            target_path = self.generate_target_path(file_path, category)

            # 检查目标文件是否已存在
            status = "pending"
            error = None
            if target_path.exists():
                status = "skipped"
                error = "目标文件已存在"

            items.append(OrganizeItem(
                source_path=file_path,
                target_path=target_path,
                category=category.name,
                status=status,
                error=error
            ))

        return items

    def execute_organize(self, items: List[OrganizeItem]) -> OrganizeResult:
        """执行文件整理"""
        result = OrganizeResult(total=len(items))

        for item in items:
            if item.status == "skipped":
                result.skipped += 1
                continue

            try:
                # 创建目标目录
                item.target_path.parent.mkdir(parents=True, exist_ok=True)

                # 移动文件
                shutil.move(str(item.source_path), str(item.target_path))
                item.status = "success"
                result.moved += 1

            except Exception as e:
                item.status = "failed"
                item.error = str(e)
                result.failed += 1

        result.items = items
        return result


# CLI命令定义
@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("-m", "--mode", type=click.Choice(["type", "date", "mixed"]),
              default="type", help="整理模式")
@click.option("-r", "--recursive", is_flag=True, help="递归处理子目录")
@click.option("-y", "--yes", is_flag=True, help="跳过确认提示")
@click.pass_context
def organize_cmd(ctx, path, mode, recursive, yes):
    """
    自动整理文件到分类目录

    PATH: 要整理的目录路径（默认为当前目录）
    """
    config = ctx.obj["config"]

    # 创建整理配置
    organize_config = OrganizeConfig(
        path=path,
        mode=mode,
        recursive=recursive,
        dry_run=not yes,  # 如果指定了-y，则关闭预览模式
        skip_confirm=yes
    )

    try:
        with logfire.span("file_organize", attributes={
            "path": path,
            "mode": mode,
            "recursive": recursive
        }):
            # 创建整理工具实例
            organizer = FileOrganizerTool(organize_config)

            # 创建整理计划
            items = organizer.create_organize_plan()

            if not items:
                click.echo("没有找到需要整理的文件。")
                return

            # 统计分析
            category_stats = {}
            for item in items:
                if item.category not in category_stats:
                    category_stats[item.category] = []
                category_stats[item.category].append(item)

            # 显示扫描结果
            click.echo(f"\n扫描目录: {os.path.abspath(path)}")
            click.echo(f"整理模式: {_get_mode_desc(mode)}")
            click.echo(f"找到 {len(items)} 个文件需要整理\n")

            # 显示整理计划
            click.echo("整理计划：")
            for category_name, category_items in category_stats.items():
                # 找到对应的图标
                icon = "📁"
                for cat in organizer.CATEGORIES:
                    if cat.name == category_name:
                        icon = cat.icon
                        break

                pending_count = len([i for i in category_items if i.status == "pending"])
                if pending_count > 0:
                    target_dir = category_items[0].target_path.parent
                    rel_target = os.path.relpath(target_dir, path)
                    click.echo(f"{icon} {category_name} ({pending_count}个文件) → {rel_target}/")

                    # 显示前几个文件名
                    for item in category_items[:3]:
                        if item.status == "pending":
                            click.echo(f"  • {item.source_path.name}")

                    if len(category_items) > 3:
                        click.echo(f"  ...")

            # 显示跳过的文件统计
            skipped_count = len([i for i in items if i.status == "skipped"])
            if skipped_count > 0:
                click.echo(f"\n⚠️  将跳过 {skipped_count} 个文件（目标位置已存在同名文件）")

            # 如果是预览模式，询问确认
            pending_count = len([i for i in items if i.status == "pending"])
            if organize_config.dry_run and pending_count > 0:
                click.echo(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                click.echo(f"将移动 {pending_count} 个文件")

                if not click.confirm("确认执行整理？"):
                    click.echo("操作已取消。")
                    return

            # 执行整理
            if pending_count > 0:
                click.echo("\n正在整理文件...")
                result = organizer.execute_organize(items)

                # 显示结果
                click.echo(f"\n整理完成：")
                click.echo(f"  成功移动: {result.moved} 个文件")
                if result.skipped > 0:
                    click.echo(f"  跳过: {result.skipped} 个文件")
                if result.failed > 0:
                    click.echo(f"  失败: {result.failed} 个文件")

                logfire.info("文件整理完成", attributes={
                    "moved": result.moved,
                    "skipped": result.skipped,
                    "failed": result.failed
                })
            else:
                click.echo("没有文件需要移动。")

    except Exception as e:
        logfire.error(f"文件整理失败: {str(e)}")
        raise click.ClickException(f"错误：{str(e)}")


def _get_mode_desc(mode: str) -> str:
    """获取模式描述"""
    mode_map = {
        "type": "按文件类型",
        "date": "按修改日期",
        "mixed": "按类型和日期"
    }
    return mode_map.get(mode, mode)
