from typing import Any

import click


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
