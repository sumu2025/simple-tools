"""文本替换工具 - 提供文件中文本批量替换功能."""

from pathlib import Path
from typing import Optional

import click
import logfire
from pydantic import BaseModel, Field

from simple_tools._typing import argument, command, option, pass_context  # 新增


class ReplaceConfig(BaseModel):
    """文本替换配置."""

    pattern: str = Field(..., description="替换模式 old:new")
    file: Optional[str] = Field(None, description="指定文件路径")
    path: str = Field(".", description="扫描目录路径")
    extensions: list[str] = Field(default_factory=list, description="文件扩展名过滤")
    dry_run: bool = Field(True, description="预览模式")
    skip_confirm: bool = Field(False, description="跳过确认")

    @property
    def old_text(self) -> str:
        """获取要查找的文本."""
        return self.pattern.split(":", 1)[0]

    @property
    def new_text(self) -> str:
        """获取替换后的文本."""
        parts = self.pattern.split(":", 1)
        return parts[1] if len(parts) > 1 else ""


class ReplaceResult(BaseModel):
    """替换结果."""

    file_path: Path
    match_count: int = 0
    replaced: bool = False
    error: Optional[str] = None
    preview_lines: list[str] = Field(default_factory=list)


class TextReplaceTool:
    """文本替换工具."""

    def __init__(self, config: ReplaceConfig):
        """初始化文本替换工具."""
        self.config = config
        logfire.info(
            "初始化文本替换工具",
            attributes={
                "pattern": config.pattern,
                "mode": "file" if config.file else "directory",
            },
        )

    def scan_files(self) -> list[Path]:
        """扫描需要处理的文件."""
        files = []

        if self.config.file:
            # 单文件模式
            file_path = Path(self.config.file)
            if file_path.exists() and file_path.is_file():
                files.append(file_path)
        else:
            # 目录模式
            path = Path(self.config.path)
            for file_path in path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    # 检查扩展名过滤
                    if self.config.extensions:
                        if file_path.suffix in self.config.extensions:
                            files.append(file_path)
                    else:
                        files.append(file_path)

        return files

    def process_file(self, file_path: Path, execute: bool = False) -> ReplaceResult:
        """处理单个文件的替换."""
        result = ReplaceResult(file_path=file_path)

        try:
            # 读取文件内容
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 查找匹配
            if self.config.old_text in content:
                result.match_count = content.count(self.config.old_text)

                if execute:
                    # 执行替换
                    new_content = content.replace(
                        self.config.old_text, self.config.new_text
                    )
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    result.replaced = True
                else:
                    # 生成预览
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if self.config.old_text in line:
                            old_line = f"  第 {i} 行: {line.strip()}"
                            replaced_line = line.replace(
                                self.config.old_text, self.config.new_text
                            ).strip()
                            new_line = "       → " + replaced_line
                            result.preview_lines.extend([old_line, new_line])
                            if len(result.preview_lines) >= 10:  # 限制预览行数
                                break

        except UnicodeDecodeError:
            result.error = "文件编码错误（可能不是UTF-8文本文件）"
        except PermissionError:
            result.error = "没有文件访问权限"
        except Exception as e:
            result.error = str(e)

        return result

    def _print_preview(self, matched_results: list[ReplaceResult]) -> int:
        """打印预览内容，降低run复杂度."""
        click.echo(f"找到 {len(matched_results)} 个包含匹配内容的文件：\n")
        total_matches = 0
        for result in matched_results:
            total_matches += result.match_count
            click.echo(f"📄 {result.file_path.name} ({result.match_count} 处匹配)")
            for line in result.preview_lines[:4]:  # 只显示前2组预览
                click.echo(line)
            if len(result.preview_lines) > 4:
                click.echo("  [更多匹配...]")
            click.echo()
        click.echo("━" * 60)
        click.echo(f"总计: {len(matched_results)} 个文件，{total_matches} 处替换\n")
        return total_matches

    def _do_replace(self, matched_results: list[ReplaceResult]) -> tuple[int, int]:
        """执行实际替换，降低run复杂度."""
        click.echo("正在执行替换...")
        success_count = 0
        failed_count = 0
        for result in matched_results:
            exec_result = self.process_file(result.file_path, execute=True)
            if exec_result.error:
                click.echo(f"  ✗ {result.file_path.name} - {exec_result.error}")
                failed_count += 1
            else:
                click.echo(
                    f"  ✓ {result.file_path.name} - 成功替换 {result.match_count} 处"
                )
                success_count += 1
        click.echo("\n替换完成：")
        click.echo(f"  成功: {success_count} 个文件")
        click.echo(f"  失败: {failed_count} 个文件")
        return success_count, failed_count

    def run(self) -> None:
        """执行替换流程."""
        with logfire.span(
            "text_replace",
            attributes={"pattern": self.config.pattern, "dry_run": self.config.dry_run},
        ):
            files = self.scan_files()

            if not files:
                click.echo("没有找到匹配的文件")
                return

            click.echo(f"扫描目标: {self.config.file or self.config.path}")
            if self.config.extensions:
                click.echo(f"文件过滤: {', '.join(self.config.extensions)}")
            click.echo(f'查找文本: "{self.config.old_text}"')
            click.echo(f'替换为: "{self.config.new_text}"')
            click.echo("━" * 60)

            # 预览阶段
            matched_results = []
            for file_path in files:
                result = self.process_file(file_path, execute=False)
                if result.match_count > 0:
                    matched_results.append(result)

            if not matched_results:
                click.echo("没有找到包含指定文本的文件")
                return

            total_matches = self._print_preview(matched_results)

            # 确认执行
            if not self.config.dry_run and not self.config.skip_confirm:
                if not click.confirm("确认执行替换？"):
                    click.echo("操作已取消")
                    return

            if self.config.dry_run:
                click.echo("预览模式完成，使用 --execute 执行实际替换")
                return

            # 执行替换
            success_count, failed_count = self._do_replace(matched_results)

            logfire.info(
                "文本替换完成",
                attributes={
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "total_replacements": total_matches,
                },
            )


@command()
@argument("pattern")
@option("-f", "--file", type=click.Path(exists=True), help="指定单个文件")
@option("-p", "--path", default=".", help="指定扫描目录")
@option("-e", "--extension", multiple=True, help="文件扩展名过滤（可多次使用）")
@option("--execute", is_flag=True, help="执行实际替换（默认为预览模式）")
@option("-y", "--yes", is_flag=True, help="跳过确认提示")
@pass_context
def replace_cmd(
    ctx: click.Context,
    pattern: str,
    file: str,
    path: str,
    extension: tuple[str, ...],
    execute: bool,
    yes: bool,
) -> None:
    """文本批量替换工具.

    PATTERN: 替换模式，格式为 "old:new"
    """
    try:
        # 验证pattern格式
        if ":" not in pattern:
            raise click.ClickException("错误：替换模式格式应为 'old:new'")

        config = ReplaceConfig(
            pattern=pattern,
            file=file,
            path=path,
            extensions=list(extension),
            dry_run=not execute,
            skip_confirm=yes,
        )

        tool = TextReplaceTool(config)
        tool.run()

    except click.ClickException as e:
        click.echo(str(e), err=True)
    except Exception as e:
        logfire.error(f"文本替换失败: {str(e)}")
        click.echo(f"发生未知错误：{str(e)}", err=True)
