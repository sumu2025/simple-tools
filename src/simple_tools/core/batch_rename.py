"""批量重命名工具模块."""

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console
from rich.table import Table

from ..utils.errors import ToolError
from ..utils.progress import ProgressTracker
from ..utils.smart_interactive import smart_confirm_sync


@dataclass
class RenameConfig:
    """重命名配置."""

    mode: str = "text"  # text, regex, number, case
    pattern: str = ""
    replacement: str = ""
    prefix: str = ""
    suffix: str = ""
    start_number: int = 1
    case_mode: str = "lower"  # lower, upper, title, camel, snake
    recursive: bool = False
    dry_run: bool = False
    backup: bool = False
    case_sensitive: bool = True
    file_filter: Optional[str] = None
    exclude_pattern: Optional[str] = None
    max_depth: int = 10
    interactive: bool = True


@dataclass
class RenameItem:
    """重命名项."""

    old_path: Path
    new_path: Path
    old_name: str
    new_name: str


@dataclass
class RenameResult:
    """重命名结果."""

    successful_renames: int = 0
    failed_renames: int = 0
    skipped_files: int = 0
    total_files: int = 0
    errors: list[str] = field(default_factory=list)
    renamed_files: list[tuple[str, str]] = field(default_factory=list)


class BatchRename:
    """批量重命名工具."""

    def __init__(self, console: Optional[Console] = None):
        """初始化 BatchRename."""
        self.console = console or Console()

    def rename_files(
        self,
        directory: str,
        mode: str = "text",
        pattern: str = "",
        replacement: str = "",
        prefix: str = "",
        suffix: str = "",
        start_number: int = 1,
        case_mode: str = "lower",
        recursive: bool = False,
        preview_only: bool = False,
        create_backup: bool = False,
        case_insensitive: bool = False,
        file_filter: Optional[str] = None,
        exclude_pattern: Optional[str] = None,
        max_depth: int = 10,
        interactive: bool = True,
        **kwargs: Any,
    ) -> RenameResult:
        """批量重命名文件."""
        config = self._create_config(
            mode,
            pattern,
            replacement,
            prefix,
            suffix,
            start_number,
            case_mode,
            recursive,
            preview_only,
            create_backup,
            case_insensitive,
            file_filter,
            exclude_pattern,
            max_depth,
            interactive,
        )

        # 获取文件列表
        files = self._get_files(directory, config)
        if not files:
            return RenameResult(total_files=0)

        # 生成重命名计划
        rename_plan = self._generate_rename_plan(files, config)

        # 创建结果对象并设置total_files
        result = RenameResult(total_files=len(files))

        if not rename_plan:
            return result

        # 处理预览模式
        if config.dry_run:
            return self._handle_preview_mode(rename_plan, result)

        # 处理交互模式
        if config.interactive:
            if not self._confirm_operation(rename_plan):
                result.skipped_files = len(rename_plan)
                return result

        # 执行重命名
        return self._execute_rename(rename_plan, config, result)

    def _handle_preview_mode(
        self, rename_plan: list[RenameItem], result: RenameResult
    ) -> RenameResult:
        """处理预览模式."""
        self._show_preview(rename_plan)
        result.skipped_files = len(rename_plan)
        return result

    def _create_config(
        self,
        mode: str,
        pattern: str,
        replacement: str,
        prefix: str,
        suffix: str,
        start_number: int,
        case_mode: str,
        recursive: bool,
        preview_only: bool,
        create_backup: bool,
        case_insensitive: bool,
        file_filter: Optional[str],
        exclude_pattern: Optional[str],
        max_depth: int,
        interactive: bool,
    ) -> RenameConfig:
        """创建重命名配置."""
        # 修复数字模式的参数处理
        if mode == "number" and not prefix and pattern:
            prefix = pattern

        # 修复大小写模式的参数处理
        if mode == "case" and replacement:
            case_mode = replacement

        return RenameConfig(
            mode=mode,
            pattern=pattern,
            replacement=replacement,
            prefix=prefix,
            suffix=suffix,
            start_number=start_number,
            case_mode=case_mode,
            recursive=recursive,
            dry_run=preview_only,
            backup=create_backup,
            case_sensitive=not case_insensitive,
            file_filter=file_filter,
            exclude_pattern=exclude_pattern,
            max_depth=max_depth,
            interactive=interactive,
        )

    def _confirm_operation(self, rename_plan: list[RenameItem]) -> bool:
        """确认操作."""
        self._show_preview(rename_plan)
        files_affected = [str(item.old_path) for item in rename_plan]
        preview_changes = {item.old_name: item.new_name for item in rename_plan[:5]}

        return smart_confirm_sync(
            operation="批量重命名文件",
            files_affected=files_affected,
            estimated_impact="medium" if len(rename_plan) > 10 else "low",
            preview_changes=preview_changes,
        )

    def _get_files(self, directory: str, config: RenameConfig) -> list[Path]:
        """获取文件列表."""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ToolError(f"目录不存在: {directory}")

        excluded_dirs = self._get_excluded_dirs()

        if config.recursive:
            files = self._collect_files_recursive(dir_path, config, excluded_dirs)
        else:
            files = self._collect_files_non_recursive(dir_path, config, excluded_dirs)

        # 应用排除模式过滤
        files = self._apply_exclude_pattern(files, config.exclude_pattern)

        return sorted(files)

    def _get_excluded_dirs(self) -> set[str]:
        """获取排除的目录列表."""
        return {
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

    def _should_exclude_file(self, file_path: Path, excluded_dirs: set[str]) -> bool:
        """检查是否应该排除文件."""
        return any(excluded in file_path.parts for excluded in excluded_dirs)

    def _collect_files_recursive(
        self, dir_path: Path, config: RenameConfig, excluded_dirs: set[str]
    ) -> list[Path]:
        """递归收集文件."""
        files = []
        pattern = "**/*" if config.file_filter is None else f"**/{config.file_filter}"

        for file_path in dir_path.glob(pattern):
            if self._should_exclude_file(file_path, excluded_dirs):
                continue
            if file_path.is_file():
                relative_path = file_path.relative_to(dir_path)
                if len(relative_path.parts) <= config.max_depth:
                    files.append(file_path)

        return files

    def _collect_files_non_recursive(
        self, dir_path: Path, config: RenameConfig, excluded_dirs: set[str]
    ) -> list[Path]:
        """非递归收集文件."""
        files = []
        pattern = "*" if config.file_filter is None else config.file_filter

        for file_path in dir_path.glob(pattern):
            if self._should_exclude_file(file_path, excluded_dirs):
                continue
            if file_path.is_file():
                files.append(file_path)

        return files

    def _apply_exclude_pattern(
        self, files: list[Path], exclude_pattern: Optional[str]
    ) -> list[Path]:
        """应用排除模式过滤."""
        if not exclude_pattern:
            return files

        exclude_regex = re.compile(exclude_pattern)
        return [f for f in files if not exclude_regex.search(f.name)]

    def _generate_rename_plan(
        self, files: list[Path], config: RenameConfig
    ) -> list[RenameItem]:
        """生成重命名计划."""
        rename_plan = []

        for i, file_path in enumerate(files):
            try:
                new_name = self._generate_new_name(file_path.name, i, config)
                if new_name and new_name != file_path.name:
                    new_path = file_path.parent / new_name
                    rename_plan.append(
                        RenameItem(
                            old_path=file_path,
                            new_path=new_path,
                            old_name=file_path.name,
                            new_name=new_name,
                        )
                    )
            except ToolError:
                # 让 ToolError 直接传播出去
                raise
            except Exception as e:
                self.console.print(
                    f"[red]生成重命名计划失败 {file_path.name}: {e}[/red]"
                )

        return rename_plan

    def _generate_new_name(
        self, filename: str, index: int, config: RenameConfig
    ) -> Optional[str]:
        """生成新文件名."""
        name, ext = os.path.splitext(filename)

        # 根据模式生成新名称
        new_name = self._apply_rename_mode(name, index, config)
        if new_name is None:
            return None

        # 添加前缀和后缀（除了number模式）
        if config.mode != "number":
            new_name = self._apply_prefix_suffix(new_name, config)

        return new_name + ext

    def _apply_rename_mode(
        self, name: str, index: int, config: RenameConfig
    ) -> Optional[str]:
        """应用重命名模式."""
        if config.mode == "text":
            return self._apply_text_mode(name, config)
        elif config.mode == "regex":
            return self._apply_regex_mode(name, config)
        elif config.mode == "number":
            return self._apply_number_mode(index, config)
        elif config.mode == "case":
            return self._apply_case_mode(name, config)
        else:
            return None

    def _apply_text_mode(self, name: str, config: RenameConfig) -> Optional[str]:
        """应用文本替换模式."""
        if config.case_sensitive:
            if config.pattern in name:
                return name.replace(config.pattern, config.replacement)
            else:
                return None
        else:
            return self._apply_case_insensitive_replace(name, config)

    def _apply_case_insensitive_replace(
        self, name: str, config: RenameConfig
    ) -> Optional[str]:
        """应用大小写不敏感的文本替换."""
        pattern_lower = config.pattern.lower()
        name_lower = name.lower()

        if pattern_lower not in name_lower:
            return None

        # 找到所有匹配位置并替换
        start = 0
        new_name = name
        while True:
            pos = name_lower.find(pattern_lower, start)
            if pos == -1:
                break
            # 替换原始字符串中对应位置的文本
            new_name = (
                new_name[:pos]
                + config.replacement
                + new_name[pos + len(config.pattern) :]
            )
            # 更新搜索位置和小写版本
            name_lower = new_name.lower()
            start = pos + len(config.replacement)

        return new_name

    def _apply_regex_mode(self, name: str, config: RenameConfig) -> Optional[str]:
        """应用正则表达式模式."""
        if not config.pattern:
            return None

        try:
            flags = 0 if config.case_sensitive else re.IGNORECASE
            new_name = re.sub(config.pattern, config.replacement, name, flags=flags)
            return new_name if new_name != name else None
        except re.error as e:
            raise ToolError(f"无效的正则表达式 '{config.pattern}': {str(e)}")

    def _apply_number_mode(self, index: int, config: RenameConfig) -> str:
        """应用数字模式."""
        number = config.start_number + index
        return f"{config.prefix}{number:03d}"

    def _apply_case_mode(self, name: str, config: RenameConfig) -> Optional[str]:
        """应用大小写转换模式."""
        case_handlers = {
            "lower": lambda n: n.lower(),
            "upper": lambda n: n.upper(),
            "title": lambda n: n.title(),
            "camel": self._to_camel_case,
            "snake": self._to_snake_case,
        }

        handler = case_handlers.get(config.case_mode)
        if not handler:
            return None

        new_name = handler(name)
        return new_name if new_name != name else None

    def _to_camel_case(self, name: str) -> str:
        """转换为驼峰命名."""
        words = re.split(r"[_\s-]+", name.lower())
        return words[0] + "".join(word.capitalize() for word in words[1:])

    def _to_snake_case(self, name: str) -> str:
        """转换为蛇形命名."""
        return re.sub(r"[\s-]+", "_", name.lower())

    def _apply_prefix_suffix(self, name: str, config: RenameConfig) -> str:
        """应用前缀和后缀."""
        if config.prefix:
            name = config.prefix + name
        if config.suffix:
            name = name + config.suffix
        return name

    def _show_preview(self, rename_plan: list[RenameItem]) -> None:
        """显示重命名预览."""
        if not rename_plan:
            self.console.print("[yellow]没有找到需要重命名的文件[/yellow]")
            return

        table = Table(title="重命名预览")
        table.add_column("原文件名", style="cyan")
        table.add_column("新文件名", style="green")

        display_items = rename_plan[:10]
        for item in display_items:
            table.add_row(item.old_name, item.new_name)

        if len(rename_plan) > 10:
            table.add_row("...", f"... (还有 {len(rename_plan) - 10} 个文件)")

        self.console.print(table)
        self.console.print(f"\n[bold]总计: {len(rename_plan)} 个文件将被重命名[/bold]")

    def _execute_rename(
        self, rename_plan: list[RenameItem], config: RenameConfig, result: RenameResult
    ) -> RenameResult:
        """执行重命名操作."""
        with ProgressTracker(
            total=len(rename_plan), description="重命名文件"
        ) as progress:
            for item in rename_plan:
                try:
                    self._rename_single_file(item, config, result)
                except Exception as e:
                    result.failed_renames += 1
                    result.errors.append(f"重命名失败 {item.old_name}: {str(e)}")
                progress.update(1)

        return result

    def _rename_single_file(
        self, item: RenameItem, config: RenameConfig, result: RenameResult
    ) -> None:
        """重命名单个文件."""
        # 检查是否是大小写不同的同一文件（macOS文件系统问题）
        if item.new_path.exists():
            if item.old_path.samefile(item.new_path):
                # 这是同一个文件，只是大小写不同，需要特殊处理
                self._handle_case_only_rename(item, result)
            else:
                # 真的是不同的文件
                result.skipped_files += 1
                result.errors.append(f"目标文件已存在: {item.new_name}")
            return

        if config.backup:
            backup_path = item.old_path.with_suffix(item.old_path.suffix + ".bak")
            shutil.copy2(item.old_path, backup_path)

        item.old_path.rename(item.new_path)
        result.successful_renames += 1
        result.renamed_files.append((item.old_name, item.new_name))

    def _handle_case_only_rename(self, item: RenameItem, result: RenameResult) -> None:
        """处理仅大小写不同的重命名."""
        temp_path = item.old_path.with_name(f"_temp_{item.old_name}")
        item.old_path.rename(temp_path)
        temp_path.rename(item.new_path)
        result.successful_renames += 1
        result.renamed_files.append((item.old_name, item.new_name))


@click.command(name="rename")
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "--mode",
    "-m",
    default="text",
    type=click.Choice(["text", "regex", "number", "case"]),
    help="重命名模式",
)
@click.option("--pattern", "-p", default="", help="搜索模式")
@click.option("--replacement", "-r", default="", help="替换文本")
@click.option("--prefix", default="", help="文件名前缀")
@click.option("--suffix", default="", help="文件名后缀")
@click.option("--start-number", default=1, help="起始数字")
@click.option(
    "--case-mode",
    default="lower",
    type=click.Choice(["lower", "upper", "title", "camel", "snake"]),
    help="大小写模式",
)
@click.option("--recursive", "-R", is_flag=True, help="递归处理子目录")
@click.option("--preview", is_flag=True, help="仅预览，不执行")
@click.option("--backup", is_flag=True, help="创建备份文件")
@click.option("--case-insensitive", "-i", is_flag=True, help="忽略大小写")
@click.option("--file-filter", "--filter", help="文件过滤器")
@click.option("--exclude", help="排除模式")
@click.option("--max-depth", default=10, help="最大递归深度")
@click.option(
    "--format",
    type=click.Choice(["plain", "json", "csv"], case_sensitive=False),
    default=None,
    help="输出格式（plain/json/csv）",
)
@click.option("--execute", is_flag=True, help="直接执行，跳过确认")
@click.option("--skip-confirm", is_flag=True, help="跳过确认")
@click.pass_context
def rename_cmd(
    ctx: click.Context,
    directory: str,
    mode: str,
    pattern: str,
    replacement: str,
    prefix: str,
    suffix: str,
    start_number: int,
    case_mode: str,
    recursive: bool,
    preview: bool,
    backup: bool,
    case_insensitive: bool,
    file_filter: Optional[str],
    exclude: Optional[str],
    max_depth: int,
    format: Optional[str],
    execute: bool,
    skip_confirm: bool,
) -> None:
    """批量重命名文件."""
    console = Console()

    # 准备参数
    format = _get_output_format(ctx, format)
    interactive = not (execute or skip_confirm or preview)

    # 执行重命名
    result = _execute_rename_command(
        console,
        directory,
        mode,
        pattern,
        replacement,
        prefix,
        suffix,
        start_number,
        case_mode,
        recursive,
        preview,
        backup,
        case_insensitive,
        file_filter,
        exclude,
        max_depth,
        interactive,
    )

    # 输出结果
    _output_results(console, result, format)

    # 记录历史
    _record_operation_history(
        directory, mode, pattern, replacement, recursive, backup, preview, result
    )


def _execute_rename_command(
    console: Console,
    directory: str,
    mode: str,
    pattern: str,
    replacement: str,
    prefix: str,
    suffix: str,
    start_number: int,
    case_mode: str,
    recursive: bool,
    preview: bool,
    backup: bool,
    case_insensitive: bool,
    file_filter: Optional[str],
    exclude: Optional[str],
    max_depth: int,
    interactive: bool,
) -> RenameResult:
    """执行重命名命令."""
    try:
        batch_rename = BatchRename(console=console)
        return batch_rename.rename_files(
            directory=directory,
            mode=mode,
            pattern=pattern,
            replacement=replacement,
            prefix=prefix,
            suffix=suffix,
            start_number=start_number,
            case_mode=case_mode,
            recursive=recursive,
            preview_only=preview,
            create_backup=backup,
            case_insensitive=case_insensitive,
            file_filter=file_filter,
            exclude_pattern=exclude,
            max_depth=max_depth,
            interactive=interactive,
        )
    except ToolError as e:
        console.print(f"[red]执行失败: {e}[/red]")
        raise click.ClickException(str(e))
    except Exception as e:
        console.print(f"[red]执行失败: {e}[/red]")
        raise click.ClickException(str(e))


def _get_output_format(ctx: click.Context, format: Optional[str]) -> str:
    """获取输出格式."""
    if format is not None:
        return format

    config = ctx.obj.get("config") if ctx.obj else None
    return config.format if config and hasattr(config, "format") else "plain"


def _output_results(console: Console, result: RenameResult, format: str) -> None:
    """输出结果."""
    if format != "plain":
        _output_formatted_results(result, format)
    else:
        _output_plain_results(console, result)


def _output_formatted_results(result: RenameResult, format: str) -> None:
    """输出格式化结果."""
    from ..utils.formatter import RenameData, format_output

    # 准备结果数据
    results = []
    for old_name, new_name in result.renamed_files:
        results.append(
            {
                "old_path": old_name,
                "new_path": new_name,
                "status": "success",
                "error": None,
            }
        )

    # 添加失败的文件
    for error in result.errors:
        if ": " in error:
            file_name = error.split(": ")[0].replace("重命名失败 ", "")
            results.append(
                {
                    "old_path": file_name,
                    "new_path": "",
                    "status": "failed",
                    "error": error,
                }
            )

    # 创建数据模型并输出
    data = RenameData(total=result.total_files, results=results)
    output = format_output(data, format)
    click.echo(output)


def _output_plain_results(console: Console, result: RenameResult) -> None:
    """输出纯文本结果."""
    if result.successful_renames > 0:
        console.print(f"[green]成功重命名: {result.successful_renames} 个文件[/green]")
    if result.failed_renames > 0:
        console.print(f"[red]重命名失败: {result.failed_renames} 个文件[/red]")
    if result.skipped_files > 0:
        console.print(f"[yellow]跳过: {result.skipped_files} 个文件[/yellow]")

    # 如果没有任何操作，输出提示信息
    if (
        result.successful_renames == 0
        and result.failed_renames == 0
        and result.skipped_files == 0
    ):
        console.print("[yellow]没有找到匹配的文件[/yellow]")

    for error in result.errors:
        console.print(f"[red]错误: {error}[/red]")


def _record_operation_history(
    directory: str,
    mode: str,
    pattern: str,
    replacement: str,
    recursive: bool,
    backup: bool,
    preview: bool,
    result: RenameResult,
) -> None:
    """记录操作历史."""
    from ..utils.smart_interactive import operation_history

    operation_data = {
        "directory": directory,
        "mode": mode,
        "pattern": pattern,
        "replacement": replacement,
        "recursive": recursive,
        "preview": preview,
    }

    if preview:
        # 预览模式：记录预览信息
        result_data = {
            "total_files": result.total_files,
            "planned_renames": result.skipped_files,
            "status": "preview",
        }
    elif result.successful_renames > 0 or result.failed_renames > 0:
        # 执行模式：记录实际结果
        operation_data["backup"] = backup
        result_data = {
            "total_files": result.total_files,
            "successful": result.successful_renames,
            "failed": result.failed_renames,
            "skipped": result.skipped_files,
            "status": "executed",
        }
    else:
        return  # 没有操作，不记录

    operation_history.add("rename", operation_data, result_data)
