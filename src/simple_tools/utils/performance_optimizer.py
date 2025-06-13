"""性能优化系统模块.

提供Logfire监控优化、分块文件处理和高效目录扫描功能。
使用 Python 3.13 的现代特性和 Pydantic v2 的性能优化。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

import logfire
from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class PerformanceMetrics(BaseModel):
    """性能指标模型."""

    operation_name: str = Field(description="操作名称")
    start_time: float = Field(description="开始时间")
    end_time: float | None = Field(default=None, description="结束时间")
    memory_usage: int | None = Field(default=None, description="内存使用量(bytes)")
    items_processed: int = Field(default=0, description="处理项目数")
    chunk_size: int | None = Field(default=None, description="分块大小")

    @computed_field
    @property
    def duration(self) -> float:
        """计算执行时长."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @computed_field
    @property
    def throughput(self) -> float:
        """计算吞吐量 (items/second)."""
        duration = self.duration
        if duration <= 0:
            return 0.0
        return self.items_processed / duration

    @computed_field
    @property
    def performance_grade(self) -> str:
        """使用Python 3.13 match/case评估性能等级."""
        throughput = self.throughput
        match (throughput, self.items_processed):
            case (t, n) if t > 1000 and n > 100:
                return "excellent"
            case (t, n) if t > 500 or n > 50:
                return "good"
            case (t, n) if t > 100 or n > 10:
                return "fair"
            case _:
                return "needs_improvement"


class ChunkProcessor:
    """分块处理器 - 优化大文件和批量操作性能."""

    def __init__(self, chunk_size: int = 1000, max_memory_mb: int = 100):
        """初始化 ChunkProcessor."""
        self.chunk_size = chunk_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.metrics = PerformanceMetrics(
            operation_name="chunk_processing",
            start_time=time.time(),
            chunk_size=chunk_size,
        )

    def process_file_chunks(
        self, file_path: Path, processor_func: Callable[[str], str]
    ) -> Generator[str, None, None]:
        """分块处理文件内容."""
        with logfire.span("file_chunk_processing", file_path=str(file_path)) as span:
            try:
                with open(file_path, encoding="utf-8") as file:
                    chunk_count = 0
                    while True:
                        chunk = file.read(self.chunk_size)
                        if not chunk:
                            break

                        processed_chunk = processor_func(chunk)
                        yield processed_chunk

                        chunk_count += 1
                        self.metrics.items_processed = chunk_count

                        # 更新Logfire指标
                        span.set_attribute("chunks_processed", chunk_count)
                        span.set_attribute(
                            "current_throughput", self.metrics.throughput
                        )

            except Exception as e:
                logfire.error(f"文件分块处理失败: {e}", file_path=str(file_path))
                raise

    async def process_files_batch_async(
        self,
        file_paths: list[Path],
        processor_func: Callable[[Path], Any],
        max_concurrent: int = 5,
    ) -> AsyncGenerator[tuple[Path, Any], None]:
        """异步批量处理文件."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single_file(file_path: Path) -> tuple[Path, Any]:
            async with semaphore:
                with logfire.span("async_file_processing", file_path=str(file_path)):
                    # 在线程池中执行同步处理函数
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, processor_func, file_path)
                    return file_path, result

        # 创建所有任务
        tasks = [process_single_file(path) for path in file_paths]

        # 逐个yield结果
        for coro in asyncio.as_completed(tasks):
            result = await coro
            self.metrics.items_processed += 1
            yield result


class DirectoryScanner:
    """高效目录扫描器."""

    def __init__(self, max_depth: int = 10, ignore_patterns: list[str] | None = None):
        """初始化 DirectoryScanner."""
        self.max_depth = max_depth
        self.ignore_patterns = ignore_patterns or [".git", "__pycache__", ".DS_Store"]
        self.scan_metrics = PerformanceMetrics(
            operation_name="directory_scanning", start_time=time.time()
        )

    def _should_ignore(self, path: Path) -> bool:
        """检查是否应该忽略路径."""
        return any(pattern in path.name for pattern in self.ignore_patterns)

    def _process_file(
        self,
        item: Path,
        file_filter: Callable[[Path], bool] | None,
        file_count: list[int],
        span: Any,
    ) -> bool:
        """处理单个文件."""
        if file_filter is None or file_filter(item):
            file_count[0] += 1
            self.scan_metrics.items_processed = file_count[0]

            # 定期更新Logfire指标
            if file_count[0] % 100 == 0:
                span.set_attribute("files_found", file_count[0])
                span.set_attribute("scan_throughput", self.scan_metrics.throughput)
            return True
        return False

    def _scan_recursive(
        self,
        current_path: Path,
        current_depth: int,
        file_filter: Callable[[Path], bool] | None,
        file_count: list[int],
        span: Any,
    ) -> Generator[Path, None, None]:
        """递归扫描目录."""
        if current_depth > self.max_depth:
            return

        try:
            for item in current_path.iterdir():
                if self._should_ignore(item):
                    continue

                if item.is_file():
                    if self._process_file(item, file_filter, file_count, span):
                        yield item
                elif item.is_dir():
                    yield from self._scan_recursive(
                        item, current_depth + 1, file_filter, file_count, span
                    )

        except PermissionError:
            logfire.warn(f"权限不足，跳过目录: {current_path}")
        except Exception as e:
            logfire.error(f"扫描目录时出错: {e}", directory=str(current_path))

    def scan_directory_optimized(
        self, root_path: Path, file_filter: Callable[[Path], bool] | None = None
    ) -> Generator[Path, None, None]:
        """优化的目录扫描，使用生成器减少内存占用."""
        with logfire.span("optimized_directory_scan", root_path=str(root_path)) as span:
            # 使用列表来保存计数，以便在嵌套函数中修改
            file_count = [0]

            yield from self._scan_recursive(root_path, 0, file_filter, file_count, span)

            # 最终指标更新
            span.set_attribute("total_files_found", file_count[0])
            span.set_attribute("final_throughput", self.scan_metrics.throughput)


class PerformanceMonitor:
    """性能监控装饰器和上下文管理器."""

    @staticmethod
    def monitor_performance(operation_name: str) -> Callable[[F], F]:
        """性能监控装饰器."""

        def decorator(func: F) -> F:
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                metrics = PerformanceMetrics(
                    operation_name=operation_name, start_time=time.time()
                )

                with logfire.span(f"monitored_{operation_name}") as span:
                    # 设置初始属性
                    span.set_attributes(metrics.model_dump(exclude={"end_time"}))

                    try:
                        result = func(*args, **kwargs)
                        metrics.end_time = time.time()

                        # 更新最终指标
                        span.set_attributes(
                            {
                                "duration": metrics.duration,
                                "performance_grade": metrics.performance_grade,
                            }
                        )

                        logfire.info(
                            f"操作完成: {operation_name}", **metrics.model_dump()
                        )

                        return result

                    except Exception as e:
                        metrics.end_time = time.time()
                        logfire.error(
                            f"操作失败: {operation_name}",
                            error=str(e),
                            **metrics.model_dump(),
                        )
                        raise

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                metrics = PerformanceMetrics(
                    operation_name=operation_name, start_time=time.time()
                )

                with logfire.span(f"async_monitored_{operation_name}") as span:
                    span.set_attributes(metrics.model_dump(exclude={"end_time"}))

                    try:
                        result = await func(*args, **kwargs)
                        metrics.end_time = time.time()

                        span.set_attributes(
                            {
                                "duration": metrics.duration,
                                "performance_grade": metrics.performance_grade,
                            }
                        )

                        return result

                    except Exception as e:
                        metrics.end_time = time.time()
                        logfire.error(
                            f"异步操作失败: {operation_name}",
                            error=str(e),
                            **metrics.model_dump(),
                        )
                        raise

            # 根据函数类型返回对应的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper  # type: ignore
            else:
                return sync_wrapper  # type: ignore

        return decorator

    @staticmethod
    @contextmanager
    def performance_context(
        operation_name: str,
    ) -> Generator[PerformanceMetrics, None, None]:
        """性能监控上下文管理器."""
        metrics = PerformanceMetrics(
            operation_name=operation_name, start_time=time.time()
        )

        with logfire.span(f"context_{operation_name}") as span:
            span.set_attributes(metrics.model_dump(exclude={"end_time"}))

            try:
                yield metrics
            finally:
                metrics.end_time = time.time()
                span.set_attributes(
                    {
                        "duration": metrics.duration,
                        "items_processed": metrics.items_processed,
                        "throughput": metrics.throughput,
                        "performance_grade": metrics.performance_grade,
                    }
                )


# 便捷函数和工具
def optimize_batch_operation(
    items: list[T],
    processor_func: Callable[[T], Any],
    chunk_size: int = 100,
    operation_name: str = "batch_operation",
) -> list[Any]:
    """优化批量操作处理."""
    with PerformanceMonitor.performance_context(operation_name) as metrics:
        results = []

        # 分块处理
        for i in range(0, len(items), chunk_size):
            chunk = items[i : i + chunk_size]
            chunk_results = [processor_func(item) for item in chunk]
            results.extend(chunk_results)

            metrics.items_processed += len(chunk)

            # 定期记录进度
            if i % (chunk_size * 10) == 0:
                logfire.info(
                    f"批量操作进度: {metrics.items_processed}/{len(items)}",
                    progress_percent=metrics.items_processed / len(items) * 100,
                )

        return results


async def optimize_async_batch_operation(
    items: list[T],
    async_processor_func: Callable[[T], Any],
    max_concurrent: int = 10,
    operation_name: str = "async_batch_operation",
) -> list[Any]:
    """优化异步批量操作处理."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(item: T) -> Any:
        async with semaphore:
            return await async_processor_func(item)

    with PerformanceMonitor.performance_context(operation_name) as metrics:
        tasks = [process_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks)
        metrics.items_processed = len(items)
        return results


# 使用示例装饰器
@PerformanceMonitor.monitor_performance("file_processing")
def process_large_file(file_path: Path) -> dict[str, Any]:
    """处理大文件的示例函数."""
    processor = ChunkProcessor(chunk_size=8192)

    def line_counter(chunk: str) -> str:
        return chunk  # 简单示例

    total_chunks = 0
    for chunk in processor.process_file_chunks(file_path, line_counter):
        total_chunks += 1

    return {
        "file_path": str(file_path),
        "total_chunks": total_chunks,
        "processing_time": processor.metrics.duration,
    }
