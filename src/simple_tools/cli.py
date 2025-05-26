"""
命令行入口 - 使用Click框架实现命令行界面
"""

import click
import logfire
from . import __version__
from .config import get_config


@click.group()
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True, help="显示详细日志信息")
@click.pass_context
def cli(ctx, verbose):
    """
    简单工具集 - 一组实用的文件和文本处理工具
    """
    # 创建上下文对象，用于在命令间共享配置
    ctx.ensure_object(dict)

    # 更新配置中的verbose选项
    config = get_config()
    config.verbose = verbose

    # 将配置存储在上下文中
    ctx.obj["config"] = config

    # 使用Logfire记录命令执行
    with logfire.span("cli_command", attributes={"verbose": verbose}):
        pass  # 实际操作在子命令中执行


# 导入各个工具的命令
from .core.file_tool import list_cmd
from .core.duplicate_finder import duplicates_cmd
from .core.batch_rename import rename_cmd
from .core.text_replace import replace_cmd
from .core.file_organizer import organize_cmd


# 注册命令到CLI
cli.add_command(list_cmd, name="list")
cli.add_command(duplicates_cmd, name="duplicates")
cli.add_command(rename_cmd, name="rename")
cli.add_command(replace_cmd, name="replace")
cli.add_command(organize_cmd, name="organize")


if __name__ == "__main__":
    cli()
