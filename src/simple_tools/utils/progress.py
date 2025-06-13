"""进度显示工具模块."""

from collections.abc import Iterable
from types import TracebackType
from typing import Any, Callable, Optional

import click


class ProgressTracker:
    """进度跟踪器上下文管理器."""

    def __init__(self, total: int, description: str = "处理中"):
        """初始化进度跟踪器.

        Args:
            total: 总项目数
            description: 进度描述

        """
        self.total = total
        self.description = description
        self.current = 0
        self.progress_bar: Optional[Any] = None  # ProgressBar type

    def __enter__(self) -> "ProgressTracker":
        """进入上下文管理器."""
        if self.total > 0:
            self.progress_bar = click.progressbar(
                length=self.total, label=self.description
            )
            if self.progress_bar is not None:
                self.progress_bar.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """退出上下文管理器."""
        if self.progress_bar:
            self.progress_bar.__exit__(exc_type, exc_val, exc_tb)

    def update(self, step: int = 1) -> None:
        """更新进度."""
        self.current += step
        if self.progress_bar:
            self.progress_bar.update(step)


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
