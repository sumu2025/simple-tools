"""CLI主模块."""

# 修改 src/simple_tools/cli.py
from typing import Optional

import click
import logfire

from simple_tools._typing import group, option, pass_context

from .config import get_config
from .core.batch_rename import rename_cmd
from .core.duplicate_finder import duplicates_cmd
from .core.file_organizer import organize_cmd
from .core.file_tool import list_cmd
from .core.summarize_cmd import summarize
from .core.text_replace import replace_cmd
from .utils.config_loader import ConfigLoader
from .utils.smart_interactive import (
    command_suggester,
    operation_history,
)


# 自定义命令不存在时的错误处理
class SmartGroup(click.Group):
    """增强的命令组，提供智能命令建议."""

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        """获取命令，如果不存在则提供建议."""
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # 命令不存在，提供建议
        command_suggester.show_help(cmd_name, f"命令 '{cmd_name}' 不存在")
        ctx.fail(f"未知命令: {cmd_name}")


# 定义主 CLI
@group(cls=SmartGroup)
@option("-v", "--verbose", is_flag=True, help="显示详细日志信息")
@option("-c", "--config", type=click.Path(exists=True), help="指定配置文件路径")
@pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """简单工具集 - 一组实用的文件和文本处理工具.

    使用 'tools COMMAND --help' 查看具体命令的帮助信息。
    使用 'tools history' 查看操作历史记录。
    """
    # 创建上下文对象，用于在命令间共享配置
    ctx.ensure_object(dict)

    # 加载配置文件
    loader = ConfigLoader()
    if config:
        tool_config = loader.load_config(config)
    else:
        tool_config = loader.load_from_directory()

    # 命令行参数覆盖配置文件 (包括 verbose)
    tool_config.verbose = verbose

    # 将配置存储在上下文中
    ctx.obj["config"] = tool_config

    # 更新全局配置
    app_config = get_config()
    app_config.verbose = tool_config.verbose

    # 使用Logfire记录命令执行
    with logfire.span("cli_command", attributes={"verbose": tool_config.verbose}):
        pass  # 实际操作在子命令中执行


# 定义 history 命令
@click.command()
@click.option("-n", "--count", default=10, type=int, help="显示最近N条记录")
@click.option("--clear", is_flag=True, help="清空历史记录")
def history_cmd(count: int, clear: bool) -> None:
    """查看或管理操作历史记录.

    示例：
      tools history              # 显示最近10条记录
      tools history -n 20        # 显示最近20条记录
      tools history --clear      # 清空历史记录
    """
    if clear:
        if click.confirm("确定要清空所有历史记录吗？"):
            operation_history.clear()
            click.echo("✅ 历史记录已清空")
        else:
            click.echo("操作已取消")
    else:
        operation_history.show_recent(count)


# 注册命令到CLI
cli.add_command(list_cmd, name="list")
cli.add_command(duplicates_cmd, name="duplicates")
cli.add_command(rename_cmd, name="rename")
cli.add_command(replace_cmd, name="replace")
cli.add_command(organize_cmd, name="organize")
cli.add_command(summarize, name="summarize")
cli.add_command(history_cmd, name="history")


if __name__ == "__main__":
    cli()
