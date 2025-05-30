# src/simple_tools/utils/progress.py
"""进度显示工具模块."""
from collections.abc import Iterable
from typing import Any, Callable

import click


def process_with_progress(
    items: Iterable[Any],
    processor: Callable[[Any], Any],
    label: str = "处理中",
    threshold: int = 50,
) -> list[Any]:
    """统一的进度处理函数.

    Args:
        items: 要处理的项目列表
        processor: 处理函数
        label: 进度条标签
        threshold: 显示进度条的阈值

    Returns:
        处理后的结果列表

    """
    items_list = list(items)
    results = []

    if len(items_list) > threshold:
        # 超过阈值，显示进度条
        with click.progressbar(items_list, label=label) as bar:
            for item in bar:
                results.append(processor(item))
    else:
        # 不超过阈值，直接处理
        for item in items_list:
            results.append(processor(item))

    return results
