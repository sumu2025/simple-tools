"""智能文件分类器模块

使用DeepSeek API对文件进行智能分类，为file_organizer工具提供AI增强功能。
"""

import asyncio
import json
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import logfire
from pydantic import BaseModel, Field, field_validator

from ..utils.errors import ToolError
from .deepseek_client import DeepSeekClient
from .prompts import PromptManager


class FileInfo(BaseModel):
    """文件信息模型."""

    path: Path = Field(..., description="文件路径")
    name: str = Field(..., description="文件名")
    extension: str = Field(..., description="文件扩展名")
    size: int = Field(..., description="文件大小（字节）")
    size_human: str = Field(..., description="人类可读的文件大小")
    modified_time: datetime = Field(..., description="修改时间")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    content_preview: Optional[str] = Field(None, description="内容预览")

    @field_validator("size_human", mode="before")
    @classmethod
    def format_size(cls, v: Any, info: Any) -> str:
        """格式化文件大小为人类可读格式."""
        if isinstance(v, str) and v:  # 如果已经是字符串且非空，直接返回
            return v

        # 从Pydantic v2的info.data中获取size
        if hasattr(info, "data"):
            size = info.data.get("size", 0)
        else:
            # 如果没有data属性，尝试从init参数中获取
            return ""  # 返回空字符串，在__init__后处理

        # 转换为浮点数以便计算
        size = float(size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def __init__(self, **data: Any) -> None:
        """初始化FileInfo并确保size_human被正确设置."""
        super().__init__(**data)
        # 如果size_human为空，重新计算
        if not self.size_human:
            size = float(self.size)
            for unit in ["B", "KB", "MB", "GB"]:
                if size < 1024.0:
                    self.size_human = f"{size:.1f} {unit}"
                    break
                size /= 1024.0
            else:
                self.size_human = f"{size:.1f} TB"


class ClassificationResult(BaseModel):
    """分类结果模型."""

    file_path: Path = Field(..., description="文件路径")
    category: str = Field(..., description="分类类别")
    confidence: int = Field(..., description="置信度(0-100)")
    reason: str = Field(..., description="分类理由")
    cached: bool = Field(False, description="是否使用缓存")
    error: Optional[str] = Field(None, description="错误信息")


class BatchClassificationResult(BaseModel):
    """批量分类结果."""

    total: int = Field(0, description="总文件数")
    success: int = Field(0, description="成功分类数")
    failed: int = Field(0, description="失败数")
    results: list[ClassificationResult] = Field(
        default_factory=list, description="分类结果列表"
    )


class FileClassifier:
    """智能文件分类器."""

    # 支持内容提取的文本文件扩展名
    TEXT_EXTENSIONS = {
        ".txt",
        ".md",
        ".rst",
        ".log",
        ".csv",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".conf",
        ".py",
        ".js",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".html",
        ".css",
        ".sh",
        ".bat",
        ".sql",
    }

    # 最大内容预览长度
    MAX_PREVIEW_LENGTH = 500

    def __init__(self, client: Optional[DeepSeekClient] = None):
        """初始化分类器.

        Args:
            client: DeepSeek客户端实例，如果不提供则创建新实例

        """
        self.client = client or DeepSeekClient()
        self._category_cache: dict[str, str] = {}
        logfire.info("初始化智能文件分类器")

    def extract_file_info(self, file_path: Path) -> FileInfo:
        """提取文件信息.

        Args:
            file_path: 文件路径

        Returns:
            FileInfo: 文件信息对象

        """
        try:
            stat = file_path.stat()

            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(str(file_path))

            # 提取内容预览（仅文本文件）
            content_preview = None
            if file_path.suffix.lower() in self.TEXT_EXTENSIONS:
                content_preview = self._extract_content_preview(file_path)

            return FileInfo(
                path=file_path,
                name=file_path.name,
                extension=file_path.suffix.lower(),
                size=stat.st_size,
                size_human="",  # 将由validator自动计算
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                mime_type=mime_type,
                content_preview=content_preview,
            )
        except Exception as e:
            logfire.error(f"提取文件信息失败: {file_path} - {e}")
            raise ToolError(
                f"无法读取文件信息: {file_path}", error_code="FILE_READ_ERROR"
            )

    def _extract_content_preview(self, file_path: Path) -> Optional[str]:
        """提取文件内容预览."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read(
                    self.MAX_PREVIEW_LENGTH + 100
                )  # 读取稍多一点以判断是否需要截断
                # 清理内容，移除多余空白
                content = re.sub(r"\s+", " ", content).strip()
                if len(content) > self.MAX_PREVIEW_LENGTH:
                    content = content[: self.MAX_PREVIEW_LENGTH] + "..."
                return content
        except Exception as e:
            logfire.warning(f"无法提取文件内容: {file_path} - {e}")
            return None

    async def classify_file(
        self, file_path: Path, use_cache: bool = True
    ) -> ClassificationResult:
        """对单个文件进行智能分类.

        Args:
            file_path: 文件路径
            use_cache: 是否使用缓存

        Returns:
            ClassificationResult: 分类结果

        """
        try:
            # 提取文件信息
            file_info = self.extract_file_info(file_path)

            # 检查缓存
            cache_key = f"{file_info.extension}:{file_info.size}"
            if use_cache and cache_key in self._category_cache:
                logfire.info(f"使用缓存分类: {file_path}")
                return ClassificationResult(
                    file_path=file_path,
                    category=self._category_cache[cache_key],
                    confidence=90,  # 缓存结果给予较高置信度
                    reason="基于相似文件的历史分类",
                    cached=True,
                )

            # 生成分类prompt
            prompt = PromptManager.format(
                "file_classify",
                filename=file_info.name,
                extension=file_info.extension,
                file_size=file_info.size_human,
                modified_time=file_info.modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                content_preview=file_info.content_preview or "（无法提取内容预览）",
            )

            # 调用AI进行分类
            with logfire.span(
                "classify_file",
                attributes={"file": str(file_path), "extension": file_info.extension},
            ):
                response = await self.client.simple_chat(prompt)

                # 解析JSON响应
                result = self._parse_classification_response(response)

                # 更新缓存
                confidence_value = cast(int, result.get("confidence", 0))
                if use_cache and confidence_value >= 80:
                    self._category_cache[cache_key] = cast(str, result["category"])

                return ClassificationResult(
                    file_path=file_path,
                    category=cast(str, result.get("category", "其他")),
                    confidence=cast(int, result.get("confidence", 0)),
                    reason=cast(str, result.get("reason", "无法确定分类原因")),
                    cached=False,
                )

        except Exception as e:
            logfire.error(f"文件分类失败: {file_path} - {e}")
            return ClassificationResult(
                file_path=file_path,
                category="其他",
                confidence=0,
                reason="分类失败",
                error=str(e),
            )

    def _parse_classification_response(self, response: str) -> dict[str, Any]:
        """解析AI分类响应."""
        try:
            # 尝试直接解析JSON
            return cast(dict[str, Any], json.loads(response))
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            json_match = re.search(r"\{[^{}]*\}", response)
            if json_match:
                try:
                    return cast(dict[str, Any], json.loads(json_match.group()))
                except json.JSONDecodeError:
                    pass

            # 返回默认值
            logfire.warning(f"无法解析分类响应: {response[:100]}...")
            return {"category": "其他", "confidence": 0, "reason": "AI响应格式错误"}

    async def classify_batch(
        self, file_paths: list[Path], max_concurrent: int = 5, use_cache: bool = True
    ) -> BatchClassificationResult:
        """批量分类文件.

        Args:
            file_paths: 文件路径列表
            max_concurrent: 最大并发数
            use_cache: 是否使用缓存

        Returns:
            BatchClassificationResult: 批量分类结果

        """
        result = BatchClassificationResult(total=len(file_paths))

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def classify_with_limit(file_path: Path) -> ClassificationResult:
            async with semaphore:
                return await self.classify_file(file_path, use_cache)

        # 并发分类
        with logfire.span(
            "batch_classify",
            attributes={
                "file_count": len(file_paths),
                "max_concurrent": max_concurrent,
            },
        ):
            tasks = [classify_with_limit(fp) for fp in file_paths]
            classifications = await asyncio.gather(*tasks)

            # 统计结果
            for classification in classifications:
                result.results.append(classification)
                if classification.error:
                    result.failed += 1
                else:
                    result.success += 1

            logfire.info(f"批量分类完成: 成功={result.success}, 失败={result.failed}")

        return result

    def get_category_stats(self) -> dict[str, int]:
        """获取缓存的分类统计."""
        stats: dict[str, int] = {}
        for category in self._category_cache.values():
            stats[category] = stats.get(category, 0) + 1
        return stats
