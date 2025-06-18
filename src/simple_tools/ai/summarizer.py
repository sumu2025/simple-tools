"""文档自动摘要模块

使用DeepSeek API对各种格式的文档生成智能摘要。
支持txt、md、pdf、docx等格式。
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import logfire
from docx import Document
from pydantic import BaseModel, Field
from pypdf import PdfReader

from ..utils.errors import ToolError
from .deepseek_client import DeepSeekClient
from .prompts import PromptManager


class DocumentInfo(BaseModel):
    """文档信息模型"""

    path: Path = Field(..., description="文档路径")
    title: str = Field(..., description="文档标题")
    doc_type: str = Field(..., description="文档类型")
    word_count: int = Field(..., description="字数统计")
    content: str = Field(..., description="文档内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class SummaryResult(BaseModel):
    """摘要结果模型"""

    file_path: Path = Field(..., description="文件路径")
    summary: str = Field(..., description="摘要内容")
    word_count: int = Field(..., description="原文字数")
    summary_length: int = Field(..., description="摘要字数")
    doc_type: str = Field(..., description="文档类型")
    cached: bool = Field(False, description="是否使用缓存")
    error: Optional[str] = Field(None, description="错误信息")


class BatchSummaryResult(BaseModel):
    """批量摘要结果"""

    total: int = Field(0, description="总文件数")
    success: int = Field(0, description="成功数")
    failed: int = Field(0, description="失败数")
    results: list[SummaryResult] = Field(
        default_factory=list, description="摘要结果列表"
    )


class DocumentSummarizer:
    """文档摘要生成器"""

    SUPPORTED_FORMATS = {
        ".txt": "text",
        ".md": "markdown",
        ".rst": "restructuredtext",
        ".pdf": "pdf",
        ".docx": "word",
        ".doc": "word",
    }

    MAX_CONTENT_LENGTH = 10000

    def __init__(self, client: Optional[DeepSeekClient] = None):
        """初始化文档摘要生成器

        Args:
            client: 可选的DeepSeek客户端实例

        """
        self.client = client or DeepSeekClient()
        self._summary_cache: dict[str, str] = {}
        logfire.info("初始化文档摘要生成器")

    def extract_document_content(self, file_path: Path) -> DocumentInfo:
        """提取文档内容

        Args:
            file_path: 需要处理的文件路径

        Returns:
            DocumentInfo: 包含文档信息的对象

        Raises:
            ToolError: 当文件不存在或格式不支持时抛出

        """
        if not file_path.exists():
            raise ToolError(f"文件不存在: {file_path}", "FILE_NOT_FOUND")

        extension = file_path.suffix.lower()
        if extension not in self.SUPPORTED_FORMATS:
            raise ToolError(
                f"不支持的文档格式: {extension}",
                "UNSUPPORTED_FORMAT",
            )

        doc_type = self.SUPPORTED_FORMATS[extension]

        if doc_type in ["text", "markdown", "restructuredtext"]:
            content = self._extract_text_content(file_path)
        elif doc_type == "pdf":
            content = self._extract_pdf_content(file_path)
        elif doc_type == "word":
            content = self._extract_docx_content(file_path)
        else:
            raise ToolError(f"未实现的文档类型处理: {doc_type}", "NOT_IMPLEMENTED")

        if len(content) > self.MAX_CONTENT_LENGTH:
            content = content[: self.MAX_CONTENT_LENGTH] + "\n...(内容已截断)"

        word_count = self._count_words(content)

        return DocumentInfo(
            path=file_path,
            title=file_path.stem,
            doc_type=doc_type,
            word_count=word_count,
            content=content,
        )

    def _extract_text_content(self, file_path: Path) -> str:
        """提取文本文件内容"""
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, encoding="gbk", errors="ignore") as f:
                return f.read()

    def _extract_pdf_content(self, file_path: Path) -> str:
        """提取PDF文件内容"""
        try:
            reader = PdfReader(file_path)
            content = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content.append(text)
            return "\n".join(content)
        except Exception as e:
            logfire.error(f"PDF内容提取失败: {file_path} - {e}")
            raise ToolError(f"无法读取PDF文件: {e}", "PDF_READ_ERROR")

    def _extract_docx_content(self, file_path: Path) -> str:
        """提取Word文档内容"""
        try:
            doc = Document(str(file_path))
            content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content.append(paragraph.text)
            return "\n".join(content)
        except Exception as e:
            logfire.error(f"Word文档内容提取失败: {file_path} - {e}")
            raise ToolError(f"无法读取Word文档: {e}", "DOCX_READ_ERROR")

    def _count_words(self, text: str) -> int:
        """混合中英文字数统计"""
        chinese_chars = 0
        non_chinese_text = []

        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                chinese_chars += 1
                non_chinese_text.append(" ")
            else:
                non_chinese_text.append(char)

        english_text = "".join(non_chinese_text)
        english_text = "".join(
            [c if c.isalnum() or c.isspace() else " " for c in english_text]
        )
        english_words = len([word for word in english_text.split() if word])

        return chinese_chars + english_words

    async def summarize_document(
        self,
        file_path: Path,
        target_length: int = 200,
        language: str = "zh",
        use_cache: bool = True,
    ) -> SummaryResult:
        """生成单个文档摘要"""
        try:
            doc_info = self.extract_document_content(file_path)

            cache_key = f"{file_path}:{target_length}:{language}"
            if use_cache and cache_key in self._summary_cache:
                logfire.info(f"使用缓存摘要: {file_path}")
                return SummaryResult(
                    file_path=file_path,
                    summary=self._summary_cache[cache_key],
                    word_count=doc_info.word_count,
                    summary_length=len(self._summary_cache[cache_key]),
                    doc_type=doc_info.doc_type,
                    cached=True,
                )

            prompt = PromptManager.format(
                "document_summarize",
                title=doc_info.title,
                doc_type=doc_info.doc_type,
                word_count=doc_info.word_count,
                content=doc_info.content,
                length=target_length,
            )

            with logfire.span(
                "summarize_document",
                attributes={
                    "file": str(file_path),
                    "doc_type": doc_info.doc_type,
                    "word_count": doc_info.word_count,
                },
            ):
                summary = await self.client.simple_chat(prompt)
                summary = summary.strip().strip('"').strip("'")

                if use_cache:
                    self._summary_cache[cache_key] = summary

                return SummaryResult(
                    file_path=file_path,
                    summary=summary,
                    word_count=doc_info.word_count,
                    summary_length=len(summary),
                    doc_type=doc_info.doc_type,
                    cached=False,
                )

        except Exception as e:
            logfire.error(f"文档摘要生成失败: {file_path} - {e}")
            return SummaryResult(
                file_path=file_path,
                summary="",
                word_count=0,
                summary_length=0,
                doc_type="unknown",
                error=str(e),
            )

    async def summarize_batch(
        self,
        file_paths: list[Path],
        target_length: int = 200,
        language: str = "zh",
        max_concurrent: int = 3,
        use_cache: bool = True,
    ) -> BatchSummaryResult:
        """批量生成文档摘要

        Args:
            file_paths: 需要处理的文件路径列表
            target_length: 目标摘要长度
            language: 生成语言
            max_concurrent: 最大并发数
            use_cache: 是否使用缓存

        Returns:
            BatchSummaryResult: 批量处理结果

        """
        result = BatchSummaryResult(total=len(file_paths))
        semaphore = asyncio.Semaphore(max_concurrent)

        async def summarize_with_limit(file_path: Path) -> SummaryResult:
            async with semaphore:
                return await self.summarize_document(
                    file_path, target_length, language, use_cache
                )

        with logfire.span(
            "batch_summarize",
            attributes={
                "file_count": len(file_paths),
                "max_concurrent": max_concurrent,
            },
        ):
            tasks = [summarize_with_limit(fp) for fp in file_paths]
            summaries = await asyncio.gather(*tasks)

            for summary in summaries:
                result.results.append(summary)
                if summary.error:
                    result.failed += 1
                else:
                    result.success += 1

            logfire.info(f"批量摘要完成: 成功={result.success}, 失败={result.failed}")

        return result

    def save_summaries(
        self, results: list[SummaryResult], output_path: Path, format: str = "json"
    ) -> None:
        """保存摘要结果到文件

        Args:
            results: 摘要结果列表
            output_path: 输出文件路径
            format: 输出格式 (json/markdown)

        """
        if format == "json":
            self._save_as_json(results, output_path)
        elif format == "markdown":
            self._save_as_markdown(results, output_path)
        else:
            raise ToolError(f"不支持的输出格式: {format}", "INVALID_FORMAT")

    def _save_as_json(self, results: list[SummaryResult], output_path: Path) -> None:
        """保存为JSON格式"""
        data = []
        for result in results:
            if not result.error:
                data.append(
                    {
                        "file": str(result.file_path),
                        "summary": result.summary,
                        "word_count": result.word_count,
                        "doc_type": result.doc_type,
                    }
                )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_as_markdown(
        self, results: list[SummaryResult], output_path: Path
    ) -> None:
        """保存为Markdown格式

        Args:
            results: 摘要结果列表
            output_path: 输出文件路径

        """
        content = ["# 文档摘要汇总\n"]
        content.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        for result in results:
            if not result.error:
                content.append(f"## 📄 {result.file_path.name}\n")
                content.append(f"- 文档类型：{result.doc_type}")
                content.append(f"- 原文字数：{result.word_count}")
                content.append(f"- 摘要字数：{result.summary_length}\n")
                content.append(f"**摘要：**\n{result.summary}\n")
                content.append("---\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
