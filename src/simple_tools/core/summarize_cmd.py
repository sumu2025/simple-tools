"""文档摘要命令模块."""

import asyncio
from pathlib import Path
from typing import Optional

import click
import logfire

from simple_tools._typing import argument, command, option, pass_context

from ..ai.config import get_ai_config
from ..ai.summarizer import DocumentSummarizer
from ..utils.errors import ToolError, handle_errors
from ..utils.progress import ProgressTracker
from ..utils.smart_interactive import operation_history


def _get_format_type(ctx: click.Context, format: Optional[str]) -> str:
    """获取输出格式类型."""
    if format:
        return format

    config = ctx.obj.get("config") if ctx.obj else None
    if config and hasattr(config, "format"):
        return str(getattr(config, "format", "plain"))

    return "plain"


@handle_errors("文档摘要")
def _get_files_to_summarize(path: str, batch: bool) -> list[Path]:
    """获取需要生成摘要的文件列表."""
    path_obj = Path(path)

    if not path_obj.exists():
        raise ToolError(
            f"路径不存在: {path}",
            error_code="FILE_NOT_FOUND",
            suggestions=[
                "检查路径拼写是否正确",
                "使用绝对路径重试",
                "使用 'tools list' 查看可用文件",
            ],
        )

    if path_obj.is_file():
        return [path_obj]

    if path_obj.is_dir() and batch:
        # 收集支持的文档文件
        supported_extensions = DocumentSummarizer.SUPPORTED_FORMATS.keys()
        files: list[Path] = []
        for ext in supported_extensions:
            files.extend(path_obj.glob(f"*{ext}"))
        return sorted(files)

    raise ToolError(
        f"路径是目录但未指定 --batch 参数: {path}",
        error_code="INVALID_OPERATION",
        suggestions=[
            "添加 --batch 参数处理整个目录",
            "指定具体的文件路径",
            "使用 'tools list' 查看目录中的文件",
        ],
    )


def _check_ai_configuration() -> None:
    """检查AI配置是否可用."""
    ai_config = get_ai_config()
    if not ai_config.enabled:
        raise ToolError(
            "AI功能未启用",
            error_code="AI_DISABLED",
            suggestions=[
                "设置环境变量 SIMPLE_TOOLS_AI_ENABLED=true",
                "在配置文件中启用 AI 功能",
                "参考文档了解如何配置 AI 功能",
            ],
        )

    if not ai_config.is_configured:
        raise ToolError(
            "AI功能未配置",
            error_code="AI_NOT_CONFIGURED",
            suggestions=[
                "设置环境变量 DEEPSEEK_API_KEY",
                "在配置文件中设置 api_key",
                "参考文档了解如何获取 API 密钥",
            ],
        )


def _determine_output_format(
    ctx: click.Context, format: Optional[str], output: Optional[str]
) -> str:
    """确定输出格式."""
    format_type = _get_format_type(ctx, format)
    if output and not format:
        # 根据输出文件扩展名推断格式
        output_path = Path(output)
        if output_path.suffix == ".json":
            format_type = "json"
        elif output_path.suffix == ".md":
            format_type = "markdown"
    return format_type


def _handle_single_file_summary(
    summarizer: DocumentSummarizer,
    file: Path,
    length: int,
    language: str,
    no_cache: bool,
    format_type: str,
    output: Optional[str],
) -> None:
    """处理单文件摘要生成."""
    click.echo(f"\n正在生成文档摘要: {file.name}")
    result = asyncio.run(
        summarizer.summarize_document(
            file,
            target_length=length,
            language=language,
            use_cache=not no_cache,
        )
    )

    if result.error:
        click.echo(f"\n❌ 摘要生成失败: {result.error}", err=True)
    else:
        if format_type == "plain":
            click.echo(f"\n📄 {result.file_path.name}")
            click.echo(f"  文档类型: {result.doc_type}")
            click.echo(f"  原文字数: {result.word_count}")
            click.echo(f"  摘要字数: {result.summary_length}")
            click.echo(f"\n摘要:\n{result.summary}")

        # 保存结果
        if output:
            summarizer.save_summaries([result], Path(output), format_type)
            click.echo(f"\n✅ 摘要已保存到: {output}")

    # 记录历史
    operation_history.add(
        "summarize",
        {"file": str(file), "length": length, "language": language},
        {
            "success": not bool(result.error),
            "word_count": result.word_count,
            "summary_length": result.summary_length,
        },
    )


def _handle_batch_summary(
    summarizer: DocumentSummarizer,
    files: list[Path],
    length: int,
    language: str,
    no_cache: bool,
    format_type: str,
    output: Optional[str],
    path: str,
) -> None:
    """处理批量摘要生成."""
    click.echo(f"\n正在批量生成 {len(files)} 个文档的摘要...")

    # 使用进度条
    with ProgressTracker(total=len(files), description="生成摘要") as progress:
        batch_result = asyncio.run(
            summarizer.summarize_batch(
                files,
                target_length=length,
                language=language,
                max_concurrent=3,
                use_cache=not no_cache,
            )
        )
        progress.update(len(files))

    # 显示结果
    if format_type == "plain":
        click.echo("\n批量摘要完成:")
        click.echo(f"  成功: {batch_result.success} 个文件")
        click.echo(f"  失败: {batch_result.failed} 个文件")

        # 显示成功的摘要
        for result in batch_result.results:
            if not result.error:
                click.echo(f"\n📄 {result.file_path.name}")
                click.echo(f"  摘要: {result.summary[:100]}...")

    # 保存结果
    if output:
        success_results = [r for r in batch_result.results if not r.error]
        if success_results:
            summarizer.save_summaries(success_results, Path(output), format_type)
            click.echo(f"\n✅ {len(success_results)} 个摘要已保存到: {output}")

    # 记录历史
    operation_history.add(
        "summarize",
        {
            "path": path,
            "batch": True,
            "file_count": len(files),
            "length": length,
            "language": language,
        },
        {
            "success": batch_result.success,
            "failed": batch_result.failed,
            "total": batch_result.total,
        },
    )


@command()
@argument("path", type=click.Path(exists=False))
@option("--length", "-l", type=int, default=200, help="目标摘要长度（字数）")
@option("--language", type=str, default="zh", help="摘要语言（zh/en）")
@option("--output", "-o", type=click.Path(), help="输出文件路径")
@option("--batch", "-b", is_flag=True, help="批量处理目录中的所有文档")
@option(
    "--format",
    type=click.Choice(["plain", "json", "markdown"], case_sensitive=False),
    default=None,
    help="输出格式（plain/json/markdown）",
)
@option("--no-cache", is_flag=True, help="不使用缓存")
@pass_context
def summarize(
    ctx: click.Context,
    path: str,
    length: int,
    language: str,
    output: Optional[str],
    batch: bool,
    format: Optional[str],
    no_cache: bool,
) -> None:
    """生成文档摘要（需要配置AI功能）.

    示例：
      tools summarize report.pdf                    # 生成单个文档摘要
      tools summarize ~/Documents --batch           # 批量生成目录下所有文档摘要
      tools summarize doc.txt --length 300          # 指定摘要长度
      tools summarize . --batch -o summaries.json   # 批量摘要并保存
    """
    try:
        # 检查AI功能是否启用
        _check_ai_configuration()

        # 获取要处理的文件
        files = _get_files_to_summarize(path, batch)

        if not files:
            click.echo("没有找到支持的文档文件。")
            return

        # 确定输出格式
        format_type = _determine_output_format(ctx, format, output)

        # 创建摘要生成器
        summarizer = DocumentSummarizer()

        # 执行摘要生成
        with logfire.span(
            "document_summarize",
            attributes={
                "file_count": len(files),
                "target_length": length,
                "language": language,
                "use_cache": not no_cache,
            },
        ):
            if len(files) == 1:
                _handle_single_file_summary(
                    summarizer,
                    files[0],
                    length,
                    language,
                    no_cache,
                    format_type,
                    output,
                )
            else:
                _handle_batch_summary(
                    summarizer,
                    files,
                    length,
                    language,
                    no_cache,
                    format_type,
                    output,
                    path,
                )

    except ToolError as e:
        click.echo(e.format_message(), err=True)
        raise click.ClickException(str(e))
    except Exception as e:
        logfire.error(f"文档摘要生成失败: {e}")
        raise click.ClickException(f"生成摘要时发生错误: {str(e)}")
