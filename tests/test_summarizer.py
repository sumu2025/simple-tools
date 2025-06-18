"""文档摘要功能测试."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from simple_tools.ai.config import AIConfig
from simple_tools.ai.deepseek_client import DeepSeekClient
from simple_tools.ai.summarizer import (
    DocumentSummarizer,
    SummaryResult,
)
from simple_tools.utils.errors import ToolError


class TestDocumentSummarizer:
    """文档摘要器测试类."""

    @pytest.fixture
    def mock_ai_config(self) -> AIConfig:
        """模拟AI配置."""
        config = AIConfig(
            enabled=True,
            api_key=SecretStr("test-key"),
            api_base="https://api.test.com",
            cache_ttl=0,  # 测试时禁用缓存
        )
        return config

    @pytest.fixture
    def mock_deepseek_client(self, mock_ai_config: AIConfig) -> MagicMock:
        """模拟DeepSeek客户端."""
        client = MagicMock(spec=DeepSeekClient)
        client.config = mock_ai_config
        client.simple_chat = AsyncMock(return_value="模拟的摘要内容")
        return client

    @pytest.fixture
    def test_text_file(self, tmp_path: Path) -> Path:
        """创建测试文本文件."""
        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "这是一个测试文档。它包含了一些测试内容，用于验证摘要功能是否正常工作。"
            "文档应该足够长，以便生成有意义的摘要。" * 10,
            encoding="utf-8",
        )
        return test_file

    @pytest.fixture
    def test_md_file(self, tmp_path: Path) -> Path:
        """创建测试Markdown文件."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "# 测试标题\n\n这是一个测试文档的内容。\n\n## 子标题\n\n更多内容...",
            encoding="utf-8",
        )
        return test_file

    def test_extract_text_content(self, test_text_file: Path) -> None:
        """测试文本内容提取."""
        summarizer = DocumentSummarizer()
        doc_info = summarizer.extract_document_content(test_text_file)

        assert doc_info.path == test_text_file
        assert doc_info.title == "test"
        assert doc_info.doc_type == "text"
        assert doc_info.word_count > 0
        assert len(doc_info.content) > 0
        assert "测试文档" in doc_info.content

    def test_extract_markdown_content(self, test_md_file: Path) -> None:
        """测试Markdown内容提取."""
        summarizer = DocumentSummarizer()
        doc_info = summarizer.extract_document_content(test_md_file)

        assert doc_info.path == test_md_file
        assert doc_info.title == "test"
        assert doc_info.doc_type == "markdown"
        assert doc_info.word_count > 0
        assert "测试标题" in doc_info.content

    def test_file_not_found(self) -> None:
        """测试文件不存在的情况."""
        summarizer = DocumentSummarizer()
        non_existent = Path("/non/existent/file.txt")

        with pytest.raises(ToolError) as exc_info:
            summarizer.extract_document_content(non_existent)

        assert exc_info.value.error_code == "FILE_NOT_FOUND"

    def test_unsupported_format(self, tmp_path: Path) -> None:
        """测试不支持的文件格式."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.touch()

        summarizer = DocumentSummarizer()
        with pytest.raises(ToolError) as exc_info:
            summarizer.extract_document_content(unsupported_file)

        assert exc_info.value.error_code == "UNSUPPORTED_FORMAT"

    def test_word_count(self) -> None:
        """测试字数统计."""
        summarizer = DocumentSummarizer()

        # 纯中文
        chinese_text = "这是中文测试"
        assert summarizer._count_words(chinese_text) == 6

        # 纯英文
        english_text = "This is English test"
        assert summarizer._count_words(english_text) == 4

        # 中英文混合
        mixed_text = "这是 English 测试"
        assert summarizer._count_words(mixed_text) == 5  # 2中文 + 1英文 + 2中文

    @pytest.mark.asyncio
    async def test_summarize_document_success(
        self, test_text_file: Path, mock_deepseek_client: MagicMock
    ) -> None:
        """测试文档摘要生成成功."""
        summarizer = DocumentSummarizer(client=mock_deepseek_client)
        result = await summarizer.summarize_document(
            test_text_file, target_length=50, use_cache=False
        )

        assert isinstance(result, SummaryResult)
        assert result.file_path == test_text_file
        assert result.summary == "模拟的摘要内容"
        assert result.doc_type == "text"
        assert result.word_count > 0
        assert not result.error
        assert not result.cached

        # 验证调用了AI客户端
        mock_deepseek_client.simple_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_with_cache(
        self, test_text_file: Path, mock_deepseek_client: MagicMock
    ) -> None:
        """测试缓存功能."""
        summarizer = DocumentSummarizer(client=mock_deepseek_client)
        summarizer._summary_cache.clear()  # 确保缓存为空

        # 第一次调用
        result1 = await summarizer.summarize_document(
            test_text_file, target_length=50, use_cache=True
        )
        assert not result1.cached
        assert mock_deepseek_client.simple_chat.call_count == 1

        # 第二次调用应该使用缓存
        result2 = await summarizer.summarize_document(
            test_text_file, target_length=50, use_cache=True
        )
        assert result2.cached
        assert result2.summary == result1.summary
        # 不应该再次调用AI
        assert mock_deepseek_client.simple_chat.call_count == 1

    @pytest.mark.asyncio
    async def test_summarize_batch(
        self, tmp_path: Path, mock_deepseek_client: MagicMock
    ) -> None:
        """测试批量摘要生成."""
        # 创建多个测试文件
        files = []
        for i in range(3):
            file_path = tmp_path / f"test_{i}.txt"
            file_path.write_text(f"测试文档 {i} 的内容", encoding="utf-8")
            files.append(file_path)

        summarizer = DocumentSummarizer(client=mock_deepseek_client)
        batch_result = await summarizer.summarize_batch(
            files, target_length=50, max_concurrent=2
        )

        assert batch_result.total == 3
        assert batch_result.success == 3
        assert batch_result.failed == 0
        assert len(batch_result.results) == 3

    def test_save_summaries_json(self, tmp_path: Path) -> None:
        """测试保存为JSON格式."""
        results = [
            SummaryResult(
                file_path=Path("test1.txt"),
                summary="摘要1",
                word_count=100,
                summary_length=10,
                doc_type="text",
            ),
            SummaryResult(
                file_path=Path("test2.txt"),
                summary="摘要2",
                word_count=200,
                summary_length=20,
                doc_type="text",
            ),
        ]

        output_path = tmp_path / "summaries.json"
        summarizer = DocumentSummarizer()
        summarizer.save_summaries(results, output_path, format="json")

        assert output_path.exists()
        # 读取并验证内容
        import json

        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["summary"] == "摘要1"

    def test_save_summaries_markdown(self, tmp_path: Path) -> None:
        """测试保存为Markdown格式."""
        results = [
            SummaryResult(
                file_path=Path("test.txt"),
                summary="这是测试摘要",
                word_count=100,
                summary_length=7,
                doc_type="text",
            )
        ]

        output_path = tmp_path / "summaries.md"
        summarizer = DocumentSummarizer()
        summarizer.save_summaries(results, output_path, format="markdown")

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# 文档摘要汇总" in content
        assert "test.txt" in content
        assert "这是测试摘要" in content
