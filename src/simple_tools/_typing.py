from enum import Enum
from typing import Any, Literal

import click


# 输出格式枚举定义
class OutputFormat(str, Enum):
    """输出格式枚举."""

    PLAIN = "plain"
    JSON = "json"
    CSV = "csv"


# 类型别名，保持向后兼容
OutputFormatType = Literal["plain", "json", "csv"]


def group(*args: Any, **kwargs: Any) -> Any:
    return click.group(*args, **kwargs)


def command(*args: Any, **kwargs: Any) -> Any:
    return click.command(*args, **kwargs)


def argument(*args: Any, **kwargs: Any) -> Any:
    return click.argument(*args, **kwargs)


def option(*args: Any, **kwargs: Any) -> Any:
    return click.option(*args, **kwargs)


def pass_context(func: Any) -> Any:
    return click.pass_context(func)
