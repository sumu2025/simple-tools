"""简单工具集命令行界面模块."""

# 修改 src/simple_tools/cli.py
from typing import Optional

import click
import logfire

from simple_tools._typing import group, option, pass_context

from .config import get_config

# 导入各个工具的命令
from .core.batch_rename import rename_cmd
from .core.duplicate_finder import duplicates_cmd
from .core.file_organizer import organize_cmd
from .core.file_tool import list_cmd
from .core.text_replace import replace_cmd
from .utils.config_loader import ConfigLoader  # 确保导入 ConfigLoader


@group()
@option("-v", "--verbose", is_flag=True, help="显示详细日志信息")
@option("-c", "--config", type=click.Path(exists=True), help="指定配置文件路径")
@pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """简单工具集 - 一组实用的文件和文本处理工具."""
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


# 注册命令到CLI
cli.add_command(list_cmd, name="list")
cli.add_command(duplicates_cmd, name="duplicates")
cli.add_command(rename_cmd, name="rename")
cli.add_command(replace_cmd, name="replace")
cli.add_command(organize_cmd, name="organize")


if __name__ == "__main__":
    cli()
