"""智能文件分类器单元测试."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from simple_tools.ai.classifier import (
    FileClassifier,
    FileInfo,
)
from simple_tools.ai.deepseek_client import DeepSeekClient


class TestFileInfo:
    """FileInfo模型测试."""

    def test_file_info_creation(self) -> None:
        """测试FileInfo创建."""
        info = FileInfo(
            path=Path("/test/file.txt"),
            name="file.txt",
            extension=".txt",
            size=1024,
            size_human="",
            modified_time=datetime.now(),
            mime_type="text/plain",
            content_preview="Hello world",
        )

        assert info.name == "file.txt"
        assert info.extension == ".txt"
        assert info.size == 1024
        assert info.size_human == "1.0 KB"  # 自动计算
        assert info.mime_type == "text/plain"

    def test_size_formatting(self) -> None:
        """测试文件大小格式化."""
        # 测试不同大小
        test_cases = [
            (100, "100.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (1024 * 1024 * 1024 * 1024, "1.0 TB"),
        ]

        for size, expected in test_cases:
            info = FileInfo(
                path=Path("/test"),
                name="test",
                extension="",
                size=size,
                size_human="",
                modified_time=datetime.now(),
            )
            assert info.size_human == expected


class TestFileClassifier:
    """FileClassifier测试."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """创建mock客户端."""
        client = MagicMock(spec=DeepSeekClient)
        client.simple_chat = AsyncMock()
        return client

    @pytest.fixture
    def classifier(self, mock_client: MagicMock) -> FileClassifier:
        """创建分类器实例."""
        return FileClassifier(client=mock_client)

    def test_extract_file_info(
        self, classifier: FileClassifier, tmp_path: Path
    ) -> None:
        """测试文件信息提取."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, this is a test file.")

        # 提取信息
        info = classifier.extract_file_info(test_file)

        assert info.name == "test.txt"
        assert info.extension == ".txt"
        assert info.size == len("Hello, this is a test file.")
        assert info.content_preview == "Hello, this is a test file."

    def test_extract_file_info_binary(
        self, classifier: FileClassifier, tmp_path: Path
    ) -> None:
        """测试二进制文件信息提取."""
        # 创建二进制文件
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"\x00\x01\x02\x03")

        # 提取信息
        info = classifier.extract_file_info(test_file)

        assert info.name == "test.jpg"
        assert info.extension == ".jpg"
        assert info.content_preview is None  # 二进制文件无内容预览

    def test_extract_content_preview(
        self, classifier: FileClassifier, tmp_path: Path
    ) -> None:
        """测试内容预览提取."""
        # 创建长文本文件
        test_file = tmp_path / "long.txt"
        long_text = "a" * 600
        test_file.write_text(long_text)

        # 提取预览
        preview = classifier._extract_content_preview(test_file)

        assert len(preview) == 503  # 500 + "..."
        assert preview.endswith("...")

    @pytest.mark.asyncio
    async def test_classify_file_success(
        self, classifier: FileClassifier, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """测试成功的文件分类."""
        # 创建测试文件
        test_file = tmp_path / "report.pdf"
        test_file.write_bytes(b"PDF content")

        # 模拟AI响应
        mock_client.simple_chat.return_value = json.dumps(
            {"category": "工作文档", "confidence": 95, "reason": "PDF格式的报告文件"}
        )

        # 执行分类
        result = await classifier.classify_file(test_file)

        assert result.category == "工作文档"
        assert result.confidence == 95
        assert result.reason == "PDF格式的报告文件"
        assert not result.cached
        assert result.error is None

    @pytest.mark.asyncio
    async def test_classify_file_with_cache(
        self, classifier: FileClassifier, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """测试使用缓存的文件分类."""
        # 创建两个相同类型和大小的文件
        file1 = tmp_path / "doc1.txt"
        file2 = tmp_path / "doc2.txt"
        file1.write_text("Hello")
        file2.write_text("World")

        # 模拟AI响应
        mock_client.simple_chat.return_value = json.dumps(
            {"category": "文档", "confidence": 85, "reason": "文本文件"}
        )

        # 第一次分类
        result1 = await classifier.classify_file(file1)
        assert not result1.cached

        # 第二次分类应该使用缓存
        result2 = await classifier.classify_file(file2)
        assert result2.cached
        assert result2.category == "文档"
        assert result2.confidence == 90  # 缓存结果的置信度

        # 验证只调用了一次AI
        assert mock_client.simple_chat.call_count == 1

    @pytest.mark.asyncio
    async def test_classify_file_parse_error(
        self, classifier: FileClassifier, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """测试AI响应解析错误."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # 模拟非JSON响应
        mock_client.simple_chat.return_value = "这不是有效的JSON"

        # 执行分类
        result = await classifier.classify_file(test_file)

        assert result.category == "其他"
        assert result.confidence == 0
        assert "AI响应格式错误" in result.reason

    @pytest.mark.asyncio
    async def test_classify_file_partial_json(
        self, classifier: FileClassifier, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """测试部分JSON响应."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # 模拟包含JSON的响应
        mock_client.simple_chat.return_value = """
        根据分析，文件分类如下：
        {"category": "个人文件", "confidence": 75, "reason": "个人笔记"}
        """

        # 执行分类
        result = await classifier.classify_file(test_file)

        assert result.category == "个人文件"
        assert result.confidence == 75

    @pytest.mark.asyncio
    async def test_classify_batch(
        self, classifier: FileClassifier, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """测试批量分类."""
        # 清空缓存以避免干扰
        classifier._category_cache.clear()

        # 创建多个文件，每个文件有不同的大小以避免缓存冲突
        files = []
        for i in range(5):
            file = tmp_path / f"file{i}.txt"
            # 不同的内容大小
            file.write_text("content " * (i + 1))
            files.append(file)

        # 模拟AI响应
        responses = [
            {"category": "文档", "confidence": 90, "reason": "文本文件"},
            {"category": "个人文件", "confidence": 85, "reason": "个人笔记"},
            {"category": "工作文档", "confidence": 95, "reason": "工作相关"},
            {"category": "临时文件", "confidence": 70, "reason": "临时内容"},
            {"category": "其他", "confidence": 60, "reason": "无法确定"},
        ]

        mock_client.simple_chat.side_effect = [json.dumps(r) for r in responses]

        # 执行批量分类
        result = await classifier.classify_batch(files, max_concurrent=3)

        assert result.total == 5
        assert result.success == 5
        assert result.failed == 0
        assert len(result.results) == 5

        # 验证分类结果
        for i, classification in enumerate(result.results):
            assert classification.category == responses[i]["category"]
            assert classification.confidence == responses[i]["confidence"]

    @pytest.mark.asyncio
    async def test_classify_batch_with_errors(
        self, classifier: FileClassifier, mock_client: MagicMock, tmp_path: Path
    ) -> None:
        """测试批量分类包含错误."""
        # 清空缓存
        classifier._category_cache.clear()

        # 创建文件，每个文件有不同的大小
        files = []
        for i in range(3):
            file = tmp_path / f"file{i}.txt"
            file.write_text("test" * (i + 1))  # 不同大小
            files.append(file)

        # 模拟混合响应
        mock_client.simple_chat.side_effect = [
            json.dumps({"category": "文档", "confidence": 90, "reason": "OK"}),
            Exception("API错误"),
            json.dumps({"category": "其他", "confidence": 80, "reason": "OK"}),
        ]

        # 执行批量分类
        result = await classifier.classify_batch(files)

        assert result.total == 3
        assert result.success == 2
        assert result.failed == 1

        # 验证错误处理
        error_result = next(r for r in result.results if r.error)
        assert error_result.category == "其他"
        assert error_result.confidence == 0
        assert "API错误" in error_result.error

    def test_get_category_stats(self, classifier: FileClassifier) -> None:
        """测试分类统计."""
        # 添加缓存数据
        classifier._category_cache = {
            ".txt:100": "文档",
            ".txt:200": "文档",
            ".jpg:1000": "图片",
            ".pdf:5000": "工作文档",
        }

        # 获取统计
        stats = classifier.get_category_stats()

        assert stats["文档"] == 2
        assert stats["图片"] == 1
        assert stats["工作文档"] == 1
