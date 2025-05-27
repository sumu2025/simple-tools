"""批量重命名工具 - 支持文本替换和序号模式的文件重命名."""

import os
from pathlib import Path
from typing import Optional

import click
import logfire
from pydantic import BaseModel, Field

from simple_tools._typing import argument, command, option, pass_context  # 新增


class RenameConfig(BaseModel):
    """批量重命名配置."""

    path: str = Field(".", description="目标目录路径")
    pattern: str = Field(..., description="重命名模式")
    filter_pattern: str = Field("*", description="文件过滤模式")
    number_mode: bool = Field(False, description="是否为序号模式")
    dry_run: bool = Field(True, description="预览模式，默认启用")
    skip_confirm: bool = Field(False, description="跳过确认")


class RenameItem(BaseModel):
    """重命名项."""

    old_path: Path = Field(..., description="原始文件路径")
    new_path: Path = Field(..., description="新文件路径")
    status: str = Field("pending", description="状态：pending/success/failed/skipped")
    error: Optional[str] = Field(None, description="错误信息")


class RenameResult(BaseModel):
    """重命名结果统计."""

    total: int = Field(..., description="处理文件总数")
    success: int = Field(0, description="成功重命名数量")
    failed: int = Field(0, description="失败数量")
    skipped: int = Field(0, description="跳过数量")
    items: list[RenameItem] = Field(
        default_factory=list, description="详细重命名项列表"
    )


class BatchRenameTool:
    """批量重命名工具."""

    def __init__(self, config: RenameConfig):
        """初始化批量重命名工具.

        参数：config - 重命名配置对象.
        """
        self.config = config
        logfire.info("初始化批量重命名工具", attributes={"config": config.model_dump()})

    def _scan_files(self) -> list[Path]:
        """扫描匹配的文件.

        返回：符合过滤条件的文件路径列表.
        """
        with logfire.span("scan_files", attributes={"path": self.config.path}):
            scan_path = Path(self.config.path)
            files = []

            try:
                # 使用glob模式匹配文件
                for file_path in scan_path.glob(self.config.filter_pattern):
                    # 只处理文件，跳过目录
                    if file_path.is_file():
                        files.append(file_path)

                # 按文件名排序，确保序号模式的顺序一致
                files.sort(key=lambda x: x.name.lower())

                logfire.info(f"扫描完成，找到 {len(files)} 个匹配文件")
                return files

            except Exception as e:
                logfire.error(f"扫描文件失败: {str(e)}")
                raise

    def _parse_pattern(self, pattern: str) -> tuple[str, str]:
        """解析重命名模式.

        参数：pattern - 重命名模式字符串
        返回：(old_text, new_text) 元组.
        """
        if self.config.number_mode:
            # 序号模式：pattern作为前缀
            return ("", pattern)
        else:
            # 文本替换模式：解析 "old:new" 格式
            if ":" in pattern:
                parts = pattern.split(":", 1)
                return (parts[0], parts[1])
            else:
                raise ValueError("文本替换模式需要使用 'old:new' 格式")

    def _generate_new_name(self, file_path: Path, index: int = 0) -> tuple[Path, bool]:
        """为文件生成新名称.

        参数：
            file_path - 原始文件路径
            index - 文件索引（用于序号模式）

        返回：(新的文件路径, 是否实际发生了改变).
        """
        old_text, new_text = self._parse_pattern(self.config.pattern)

        if self.config.number_mode:
            # 序号模式：前缀_序号.扩展名
            new_name = f"{new_text}_{index+1:03d}{file_path.suffix}"
            changed = True
        else:
            # 文本替换模式：替换文件名中的指定文本
            old_name = file_path.stem  # 不包含扩展名的文件名
            new_name = old_name.replace(old_text, new_text) + file_path.suffix
            # 检查是否实际发生了替换
            changed = old_text in old_name

        # 返回同目录下的新路径和是否改变的标志
        return file_path.parent / new_name, changed

    def _check_conflicts_and_changes(self, items: list[RenameItem]) -> list[RenameItem]:
        """检查命名冲突和无效更改.

        参数：items - 重命名项列表
        返回：更新状态后的重命名项列表.
        """
        with logfire.span("check_conflicts"):
            for item in items:
                # 检查文件名是否实际发生了改变
                if item.old_path.name == item.new_path.name:
                    item.status = "skipped"
                    if self.config.number_mode:
                        item.error = "序号模式文件名未改变"
                    else:
                        old_text, _ = self._parse_pattern(self.config.pattern)
                        item.error = f"文件名中不包含要替换的文本 '{old_text}'"
                    logfire.warning(f"跳过重命名，文件名未改变: {item.old_path}")
                    continue

                # 检查目标文件是否已存在
                if item.new_path.exists():
                    item.status = "skipped"
                    item.error = f"目标文件已存在: {item.new_path.name}"
                    logfire.warning(f"跳过重命名，目标文件已存在: {item.new_path}")

            return items

    def preview_rename(self, items: list[RenameItem]) -> bool:
        """预览重命名结果并等待用户确认.

        参数：items - 重命名项列表
        返回：用户是否确认继续执行.
        """
        if not items:
            click.echo("没有找到匹配的文件")
            return False

        # 显示预览信息
        click.echo(f"\n扫描目录: {os.path.abspath(self.config.path)}")
        click.echo(f"文件过滤: {self.config.filter_pattern}")
        click.echo(f"找到 {len(items)} 个匹配文件\n")

        # 显示重命名预览
        click.echo("重命名预览：")
        valid_items = 0

        for item in items:
            if item.status == "pending":
                click.echo(f"  {item.old_path.name:<30} → {item.new_path.name}")
                valid_items += 1
            else:
                click.echo(
                    f"  {item.old_path.name:<30} → {item.new_path.name} "
                    f"(⚠️  {item.error})"
                )

        if valid_items == 0:
            click.echo("\n❌ 没有可以重命名的文件")
            return False

        # 如果跳过确认，直接返回True
        if self.config.skip_confirm:
            return True

        # 等待用户确认
        click.echo(f"\n将重命名 {valid_items} 个文件")
        confirmed = click.confirm("确认执行重命名？", default=False)
        return bool(confirmed)

    def execute_rename(self, items: list[RenameItem]) -> RenameResult:
        """执行重命名操作.

        参数：items - 重命名项列表
        返回：重命名结果统计.
        """
        with logfire.span("execute_rename", attributes={"item_count": len(items)}):
            result = RenameResult(total=len(items), items=items)

            click.echo("\n正在执行重命名...")

            for item in items:
                if item.status != "pending":
                    result.skipped += 1
                    click.echo(
                        f"  ⚠️  {item.old_path.name} → {item.new_path.name} "
                        f"({item.error})"
                    )
                    continue

                try:
                    # 执行重命名
                    item.old_path.rename(item.new_path)
                    item.status = "success"
                    result.success += 1
                    click.echo(f"  ✓ {item.old_path.name} → {item.new_path.name}")

                except Exception as e:
                    item.status = "failed"
                    item.error = str(e)
                    result.failed += 1
                    click.echo(
                        f"  ✗ {item.old_path.name} → {item.new_path.name} "
                        f"(错误: {str(e)})"
                    )
                    logfire.error(
                        f"重命名失败: {item.old_path} → {item.new_path}",
                        attributes={"error": str(e)},
                    )

            # 显示结果统计
            click.echo("\n重命名完成：")
            click.echo(f"  成功: {result.success} 个文件")
            click.echo(f"  失败: {result.failed} 个文件")
            click.echo(f"  跳过: {result.skipped} 个文件")

            logfire.info(
                "批量重命名完成",
                attributes={
                    "total": result.total,
                    "success": result.success,
                    "failed": result.failed,
                    "skipped": result.skipped,
                },
            )

            return result

    def run(self) -> RenameResult:
        """运行批量重命名主流程.

        返回：重命名结果统计.
        """
        with logfire.span("batch_rename_run"):
            logfire.info("开始批量重命名流程")

            # 1. 扫描文件
            files = self._scan_files()

            if not files:
                click.echo("没有找到匹配的文件")
                return RenameResult(total=0)

            # 2. 生成新文件名
            items = []
            for index, file_path in enumerate(files):
                try:
                    new_path, changed = self._generate_new_name(file_path, index)
                    item = RenameItem(old_path=file_path, new_path=new_path)
                    # 如果文本替换模式下文件名没有实际改变，标记状态
                    if not changed and not self.config.number_mode:
                        item.status = "skipped"
                        old_text, _ = self._parse_pattern(self.config.pattern)
                        item.error = f"文件名中不包含要替换的文本 '{old_text}'"
                    items.append(item)
                except Exception as e:
                    logfire.error(
                        f"生成新文件名失败: {file_path}", attributes={"error": str(e)}
                    )
                    raise click.ClickException(f"错误：{str(e)}")

            # 3. 检查命名冲突
            items = self._check_conflicts_and_changes(items)

            # 4. 预览模式或直接执行
            if self.config.dry_run:
                # 预览模式：显示预览并等待确认
                if not self.preview_rename(items):
                    click.echo("操作已取消")
                    return RenameResult(
                        total=len(items), skipped=len(items), items=items
                    )

            # 5. 执行重命名
            return self.execute_rename(items)


@command()
@argument("pattern", required=True)
@option("-p", "--path", type=click.Path(exists=True), default=".", help="目标目录路径")
@option("-f", "--filter", default="*", help="文件过滤模式，如 '*.jpg'")
@option("-n", "--number", is_flag=True, help="序号模式：为文件添加数字序号")
@option("--execute", is_flag=True, help="直接执行，跳过预览")
@option("-y", "--yes", is_flag=True, help="跳过确认提示")
@pass_context
def rename_cmd(
    ctx: click.Context,
    pattern: str,
    path: str,
    filter: str,
    number: bool,
    execute: bool,
    yes: bool,
) -> None:
    """批量重命名文件.

    PATTERN: 重命名模式

    - 文本替换模式: "old:new" (将文件名中的old替换为new)
    - 序号模式: 配合 --number 选项，PATTERN作为前缀

    示例用法：
      tools rename "IMG:Photo"                # 将IMG替换为Photo
      tools rename "vacation" -n              # 添加序号: vacation_001.jpg
      tools rename "test:prod" -f "*.txt"     # 只处理txt文件
      tools rename "old:new" -p ~/Documents   # 指定目录
      tools rename "draft:final" --execute    # 跳过预览直接执行
    """
    try:
        # 创建配置对象
        config = RenameConfig(
            path=path,
            pattern=pattern,
            filter_pattern=filter,
            number_mode=number,
            dry_run=not execute,  # execute为True时关闭预览模式
            skip_confirm=yes,
        )

        # 创建工具并执行
        tool = BatchRenameTool(config)
        tool.run()

    except click.ClickException:
        # Click异常直接传播
        raise
    except Exception as e:
        # 其他异常转换为Click异常
        logfire.error(f"批量重命名失败: {str(e)}")
        raise click.ClickException(f"错误：{str(e)}")
