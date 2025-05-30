# tests/test_progress.py
"""进度显示功能的测试."""
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from simple_tools.utils.progress import process_with_progress


class TestProgress:
    """进度显示测试类."""

    def test_process_without_progress_bar_when_below_threshold(self) -> None:
        """当项目数量低于阈值时，不显示进度条."""
        # 准备测试数据
        items: list[int] = [1, 2, 3, 4, 5]  # 5个项目，低于默认阈值50
        processor: MagicMock = MagicMock(side_effect=lambda x: x * 2)

        # 执行测试
        results = process_with_progress(items, processor)

        # 验证结果
        assert results == [2, 4, 6, 8, 10]
        assert processor.call_count == 5

    from unittest.mock import MagicMock

    @patch("click.progressbar")
    def test_process_with_progress_bar_when_above_threshold(
        self, mock_progressbar: MagicMock
    ) -> None:
        """当项目数量超过阈值时，显示进度条."""
        # 准备测试数据
        items: list[int] = list(range(60))  # 60个项目，超过默认阈值50
        processor: MagicMock = MagicMock(side_effect=lambda x: x * 2)

        # 模拟progressbar行为
        mock_progressbar.return_value.__enter__.return_value = items

        # 执行测试
        process_with_progress(items, processor)

        # 验证进度条被调用
        mock_progressbar.assert_called_once()
        # 验证处理器被调用了60次
        assert processor.call_count == 60

    # 在 tests/test_progress.py 中添加以下测试用例

    def test_custom_threshold(self) -> None:
        """测试自定义阈值."""
        items: list[int] = list(range(10))  # 10个项目
        processor: MagicMock = MagicMock(side_effect=lambda x: x * 2)

        # 使用阈值5，应该显示进度条
        with patch("click.progressbar") as mock_progressbar:
            mock_progressbar.return_value.__enter__.return_value = items
            process_with_progress(items, processor, threshold=5)
            mock_progressbar.assert_called_once()

    def test_custom_label(self) -> None:
        """测试自定义标签."""
        items: list[int] = list(range(60))
        processor: MagicMock = MagicMock(side_effect=lambda x: x * 2)

        with patch("click.progressbar") as mock_progressbar:
            mock_progressbar.return_value.__enter__.return_value = items
            process_with_progress(items, processor, label="计算哈希值")

            # 验证progressbar被调用时使用了自定义标签
            args, kwargs = mock_progressbar.call_args
            assert kwargs.get("label") == "计算哈希值" or args[1] == "计算哈希值"

    def test_empty_items(self) -> None:
        """测试空列表."""
        items: list[int] = []
        processor: MagicMock = MagicMock()

        results = process_with_progress(items, processor)

        assert results == []
        processor.assert_not_called()

    def test_processor_exception(self) -> None:
        """测试处理函数抛出异常."""
        items: list[int] = [1, 2, 3]
        processor: MagicMock = MagicMock(side_effect=ValueError("处理错误"))

        with pytest.raises(ValueError, match="处理错误"):
            process_with_progress(items, processor)

    # 在 tests/test_progress.py 中补充更多测试用例

    def test_progress_with_generator(self) -> None:
        """测试使用生成器作为输入."""

        def item_generator() -> Generator[int, None, None]:
            yield from range(60)

        processor: MagicMock = MagicMock(side_effect=lambda x: x * 2)

        with patch("click.progressbar") as mock_progressbar:
            mock_progressbar.return_value.__enter__.return_value = list(range(60))
            process_with_progress(item_generator(), processor)
            mock_progressbar.assert_called_once()

    def test_progress_with_string_items(self) -> None:
        """测试处理字符串项目."""
        items: list[str] = ["file1.txt", "file2.txt", "file3.txt"]
        processor: MagicMock = MagicMock(side_effect=lambda x: x.upper())

        results = process_with_progress(items, processor)

        assert results == ["FILE1.TXT", "FILE2.TXT", "FILE3.TXT"]
        assert processor.call_count == 3
