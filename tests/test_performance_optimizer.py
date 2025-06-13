"""性能优化系统测试模块."""

import asyncio
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from simple_tools.utils.performance_optimizer import (
    ChunkProcessor,
    DirectoryScanner,
    PerformanceMetrics,
    PerformanceMonitor,
    optimize_async_batch_operation,
    optimize_batch_operation,
)


class TestPerformanceMetrics:
    """测试性能指标模型."""

    def test_metrics_initialization(self) -> None:
        """测试指标初始化."""
        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=time.time(),
            items_processed=100,
            chunk_size=50,
        )

        assert metrics.operation_name == "test_op"
        assert metrics.items_processed == 100
        assert metrics.chunk_size == 50
        assert metrics.end_time is None

    def test_duration_calculation(self) -> None:
        """测试持续时间计算."""
        start = time.time()
        metrics = PerformanceMetrics(operation_name="test_op", start_time=start)

        # 模拟一些时间流逝
        time.sleep(0.1)

        # 未结束时的duration
        assert metrics.duration > 0.09  # 略小于0.1以避免时间精度问题

        # 设置结束时间
        metrics.end_time = start + 0.5
        assert abs(metrics.duration - 0.5) < 0.01

    def test_throughput_calculation(self) -> None:
        """测试吞吐量计算."""
        start = time.time()
        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=start,
            end_time=start + 2.0,  # 2秒
            items_processed=100,
        )

        assert metrics.throughput == 50.0  # 100 items / 2 seconds

        # 测试零持续时间
        metrics.end_time = start
        assert metrics.throughput == 0.0

    @pytest.mark.parametrize(
        "throughput,items,expected_grade",
        [
            (1500, 200, "excellent"),  # 高吞吐量和项目数
            (600, 60, "good"),  # 中等吞吐量
            (200, 20, "fair"),  # 一般吞吐量
            (50, 5, "needs_improvement"),  # 低吞吐量
        ],
    )
    def test_performance_grade(
        self, throughput: float, items: int, expected_grade: str
    ) -> None:
        """测试性能等级评估."""
        # 计算需要的持续时间
        duration = items / throughput if throughput > 0 else 1
        start = time.time()

        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=start,
            end_time=start + duration,
            items_processed=items,
        )

        assert metrics.performance_grade == expected_grade


class TestChunkProcessor:
    """测试分块处理器."""

    @pytest.fixture
    def temp_file(self) -> Iterator[Path]:
        """创建临时测试文件."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            # 写入测试内容
            for i in range(1000):
                f.write(f"Line {i}\n")
            temp_path = Path(f.name)

        yield temp_path

        # 清理
        temp_path.unlink(missing_ok=True)

    def test_chunk_processor_initialization(self) -> None:
        """测试分块处理器初始化."""
        processor = ChunkProcessor(chunk_size=500, max_memory_mb=50)

        assert processor.chunk_size == 500
        assert processor.max_memory_bytes == 50 * 1024 * 1024
        assert processor.metrics.operation_name == "chunk_processing"
        assert processor.metrics.chunk_size == 500

    def test_process_file_chunks(self, temp_file: Path) -> None:
        """测试文件分块处理."""
        processor = ChunkProcessor(chunk_size=100)

        def simple_processor(chunk: str) -> str:
            return chunk.upper()

        chunks = list(processor.process_file_chunks(temp_file, simple_processor))

        # 验证处理结果
        assert len(chunks) > 0
        assert all(chunk.isupper() or chunk == "" for chunk in chunks)
        assert processor.metrics.items_processed > 0

    def test_process_file_chunks_error_handling(self) -> None:
        """测试文件处理错误处理."""
        processor = ChunkProcessor()
        non_existent_file = Path("/non/existent/file.txt")

        def dummy_processor(chunk: str) -> str:
            return chunk

        with pytest.raises(FileNotFoundError):
            list(processor.process_file_chunks(non_existent_file, dummy_processor))

    @pytest.mark.asyncio
    async def test_process_files_batch_async(self, tmp_path: Path) -> None:
        """测试异步批量文件处理."""
        # 创建多个测试文件
        files = []
        for i in range(5):
            file_path = tmp_path / f"test_{i}.txt"
            file_path.write_text(f"Content {i}")
            files.append(file_path)

        processor = ChunkProcessor()

        def sync_processor(file_path: Path) -> str:
            return file_path.read_text()

        # 收集所有结果
        results = []
        async for path, result in processor.process_files_batch_async(
            files, sync_processor, max_concurrent=3
        ):
            results.append((path, result))

        # 验证结果
        assert len(results) == 5
        assert processor.metrics.items_processed == 5

        # 验证每个文件都被正确处理
        for path, result in results:
            expected = f"Content {path.stem.split('_')[1]}"
            assert result == expected


class TestDirectoryScanner:
    """测试目录扫描器."""

    @pytest.fixture
    def test_directory(self, tmp_path: Path) -> Path:
        """创建测试目录结构."""
        # 创建目录结构
        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir2").mkdir()
        (tmp_path / ".git").mkdir()  # 应该被忽略
        (tmp_path / "__pycache__").mkdir()  # 应该被忽略

        # 创建文件
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir1" / "file3.txt").write_text("content3")
        (tmp_path / "subdir2" / "file4.py").write_text("content4")
        (tmp_path / ".git" / "config").write_text("git config")

        return tmp_path

    def test_scanner_initialization(self) -> None:
        """测试扫描器初始化."""
        scanner = DirectoryScanner(max_depth=5, ignore_patterns=[".test"])

        assert scanner.max_depth == 5
        assert ".test" in scanner.ignore_patterns
        # 注意：新的 ignore_patterns 会替换默认值，而不是追加
        # 如果要保留默认值，需要在初始化时包含它们

    def test_scan_directory_optimized(self, test_directory: Path) -> None:
        """测试优化的目录扫描."""
        scanner = DirectoryScanner()

        # 扫描所有文件
        files = list(scanner.scan_directory_optimized(test_directory))

        # 验证结果
        assert len(files) == 4  # 不包括.git目录中的文件
        file_names = {f.name for f in files}
        assert "file1.txt" in file_names
        assert "file2.py" in file_names
        assert "file3.txt" in file_names
        assert "file4.py" in file_names
        assert "config" not in file_names  # .git中的文件被忽略

    def test_scan_with_file_filter(self, test_directory: Path) -> None:
        """测试带文件过滤的扫描."""
        scanner = DirectoryScanner()

        # 只扫描.txt文件
        def txt_filter(path: Path) -> bool:
            return path.suffix == ".txt"

        files = list(
            scanner.scan_directory_optimized(test_directory, file_filter=txt_filter)
        )

        # 验证结果
        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_max_depth_limit(self, tmp_path: Path) -> None:
        """测试最大深度限制."""
        # 创建深层目录结构
        deep_path = tmp_path
        for i in range(15):
            deep_path = deep_path / f"level{i}"
            deep_path.mkdir()
            (deep_path / f"file{i}.txt").write_text(f"content{i}")

        # 设置最大深度为3
        scanner = DirectoryScanner(max_depth=3)
        files = list(scanner.scan_directory_optimized(tmp_path))

        # 验证只扫描到深度3（max_depth=3 表示最多3层嵌套）
        # 深度从0开始计数，所以实际上是0,1,2层
        assert len(files) == 3  # 0, 1, 2层各一个文件

    def test_permission_error_handling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """测试权限错误处理."""
        scanner = DirectoryScanner()

        # 模拟权限错误
        def mock_iterdir(self: Path) -> None:
            raise PermissionError("Access denied")

        with monkeypatch.context() as m:
            m.setattr(Path, "iterdir", mock_iterdir)

            # 应该不抛出异常，只是记录警告
            files = list(scanner.scan_directory_optimized(tmp_path))
            assert files == []


class TestPerformanceMonitor:
    """测试性能监控器."""

    def test_monitor_performance_decorator_sync(self) -> None:
        """测试同步函数的性能监控装饰器."""

        @PerformanceMonitor.monitor_performance("test_operation")
        def test_function(x: int) -> int:
            time.sleep(0.1)
            return x * 2

        result = test_function(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_monitor_performance_decorator_async(self) -> None:
        """测试异步函数的性能监控装饰器."""

        @PerformanceMonitor.monitor_performance("async_test_operation")
        async def async_test_function(x: int) -> int:
            await asyncio.sleep(0.1)
            return x * 3

        result = await async_test_function(5)
        assert result == 15

    def test_monitor_performance_decorator_with_exception(self) -> None:
        """测试装饰器的异常处理."""

        @PerformanceMonitor.monitor_performance("failing_operation")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_performance_context_manager(self) -> None:
        """测试性能监控上下文管理器."""
        with PerformanceMonitor.performance_context("context_operation") as metrics:
            # 模拟一些处理
            time.sleep(0.1)
            metrics.items_processed = 50

        assert metrics.duration > 0.09  # 略小于0.1以避免时间精度问题
        assert metrics.items_processed == 50
        assert metrics.throughput > 0

    def test_performance_context_with_exception(self) -> None:
        """测试上下文管理器的异常处理."""
        with pytest.raises(RuntimeError):
            with PerformanceMonitor.performance_context("failing_context") as metrics:
                metrics.items_processed = 10
                raise RuntimeError("Context error")

        # 确保metrics在异常后仍然被正确更新
        assert metrics.end_time is not None
        assert metrics.items_processed == 10


class TestOptimizationFunctions:
    """测试优化函数."""

    def test_optimize_batch_operation(self) -> None:
        """测试批量操作优化."""
        items = list(range(250))

        def processor(x: int) -> int:
            return x * 2

        results = optimize_batch_operation(
            items, processor, chunk_size=50, operation_name="test_batch"
        )

        assert len(results) == 250
        assert results == [x * 2 for x in items]

    @pytest.mark.asyncio
    async def test_optimize_async_batch_operation(self) -> None:
        """测试异步批量操作优化."""
        items = list(range(100))

        async def async_processor(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 3

        results = await optimize_async_batch_operation(
            items, async_processor, max_concurrent=10, operation_name="test_async_batch"
        )

        assert len(results) == 100
        assert results == [x * 3 for x in items]

    def test_process_large_file_example(self, tmp_path: Path) -> None:
        """测试大文件处理示例."""
        # 创建测试文件
        test_file = tmp_path / "large_file.txt"
        content = "Test line\n" * 1000
        test_file.write_text(content)

        # 模拟 process_large_file 函数的功能
        @PerformanceMonitor.monitor_performance("file_processing")
        def process_file(file_path: Path) -> dict[str, int | str | float | None]:
            processor = ChunkProcessor(chunk_size=8192)

            def line_counter(chunk: str) -> str:
                return chunk

            total_chunks = 0
            for chunk in processor.process_file_chunks(file_path, line_counter):
                total_chunks += 1

            return {
                "file_path": str(file_path),
                "total_chunks": total_chunks,
                "processing_time": processor.metrics.duration,
            }

        result = process_file(test_file)

        assert result["file_path"] == str(test_file)
        assert result["total_chunks"] > 0
        assert result["processing_time"] > 0


class TestIntegration:
    """集成测试."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path: Path) -> None:
        """测试完整的工作流程."""
        # 创建测试环境
        for i in range(10):
            file_path = tmp_path / f"data_{i}.txt"
            file_path.write_text(f"Data content {i}\n" * 100)

        # 1. 扫描目录
        scanner = DirectoryScanner()
        files = list(scanner.scan_directory_optimized(tmp_path))
        assert len(files) == 10

        # 2. 批量处理文件
        processor = ChunkProcessor(chunk_size=500)

        def process_file_content(file_path: Path) -> int:
            line_count = 0
            for chunk in processor.process_file_chunks(file_path, lambda x: x.upper()):
                line_count += chunk.count("\n")
            return line_count

        # 3. 使用批量优化处理
        with PerformanceMonitor.performance_context("integration_test") as metrics:
            results = optimize_batch_operation(
                files, process_file_content, chunk_size=5
            )
            metrics.items_processed = len(files)

        # 验证结果
        assert len(results) == 10
        assert all(count == 100 for count in results)
        assert metrics.performance_grade in ["excellent", "good", "fair"]

    def test_error_propagation(self) -> None:
        """测试错误传播."""

        def failing_processor(x: int) -> int:
            if x == 5:
                raise ValueError("Processing error at 5")
            return x

        items = list(range(10))

        with pytest.raises(ValueError, match="Processing error at 5"):
            optimize_batch_operation(items, failing_processor, chunk_size=3)
