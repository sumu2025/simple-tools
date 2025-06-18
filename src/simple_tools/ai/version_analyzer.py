"""文件版本分析器.

用于分析重复文件之间的版本关系，提供智能保留建议。
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import logfire
from pydantic import BaseModel, Field, computed_field

from ..ai.config import AIConfig
from ..ai.deepseek_client import DeepSeekClient, DeepSeekMessage
from ..ai.prompts import prompt_manager


class FileVersion(BaseModel):
    """文件版本信息."""

    path: Path
    size: int
    modified_time: float
    name_pattern: str = Field(default="", description="文件名模式")
    version_indicator: Optional[str] = Field(None, description="版本标识")
    content_preview: Optional[str] = Field(None, description="内容预览")

    @computed_field
    @property
    def modified_datetime(self) -> datetime:
        """修改时间的datetime对象."""
        return datetime.fromtimestamp(self.modified_time)

    @computed_field
    @property
    def version_score(self) -> float:
        """版本评分（越高越可能是最新版本）."""
        score = 0.0

        # 时间分数（越新分数越高）
        time_score = self.modified_time / 1e10  # 归一化
        score += time_score * 0.3

        # 版本标识分数
        if self.version_indicator:
            if "final" in self.version_indicator.lower():
                score += 1.0
            elif "v" in self.version_indicator.lower():
                # 提取版本号
                match = re.search(r"v?(\d+)(?:\.(\d+))?", self.version_indicator)
                if match:
                    major = int(match.group(1))
                    minor = int(match.group(2) or 0)
                    score += (major * 10 + minor) / 100.0
            elif any(
                word in self.version_indicator.lower()
                for word in ["new", "latest", "最新"]
            ):
                score += 0.8
            elif any(
                word in self.version_indicator.lower()
                for word in ["old", "backup", "备份"]
            ):
                score -= 0.5

        # 文件名模式分数
        if "副本" in self.name_pattern or "copy" in self.name_pattern.lower():
            score -= 0.3
        if "backup" in self.name_pattern.lower() or "备份" in self.name_pattern:
            score -= 0.5

        return score


class VersionRelation(BaseModel):
    """版本关系."""

    relation_type: str = Field(..., description="关系类型: version/backup/copy")
    confidence: float = Field(..., description="置信度 0-1")
    base_file: Path = Field(..., description="基础文件")
    derived_files: list[Path] = Field(..., description="派生文件")
    reason: str = Field(..., description="判断理由")


class VersionAnalysis(BaseModel):
    """版本分析结果."""

    files: list[FileVersion]
    similarity_score: float = Field(..., description="内容相似度 0-1")
    has_version_relation: bool
    relation: Optional[VersionRelation] = None
    ai_suggestion: Optional[str] = None
    recommended_keep: Optional[Path] = None
    confidence: float = Field(0.0, description="建议置信度 0-1")


class VersionAnalyzer:
    """文件版本分析器."""

    def __init__(self, ai_config: Optional[AIConfig] = None):
        """初始化版本分析器."""
        self.ai_config = ai_config or AIConfig()
        self.ai_client = None
        if self.ai_config.enabled and self.ai_config.api_key:
            self.ai_client = DeepSeekClient(self.ai_config)

    def analyze_file_group(self, file_paths: list[Path]) -> VersionAnalysis:
        """分析一组文件的版本关系.

        Args:
            file_paths: 文件路径列表

        Returns:
            版本分析结果

        """
        with logfire.span(
            "analyze_file_group", attributes={"file_count": len(file_paths)}
        ):
            # 收集文件信息
            file_versions = self._collect_file_info(file_paths)

            # 计算文件名相似度
            similarity_score = self._calculate_name_similarity(file_versions)

            # 识别版本关系
            has_relation, relation = self._identify_version_relation(file_versions)

            # 基础分析结果
            analysis = VersionAnalysis(
                files=file_versions,
                similarity_score=similarity_score,
                has_version_relation=has_relation,
                relation=relation,
            )

            # 生成基础建议
            analysis.recommended_keep = self._generate_basic_recommendation(
                file_versions
            )
            analysis.confidence = 0.7 if has_relation else 0.5

            return analysis

    async def analyze_with_ai(self, file_paths: list[Path]) -> VersionAnalysis:
        """使用AI分析文件版本关系.

        Args:
            file_paths: 文件路径列表

        Returns:
            增强的版本分析结果

        """
        # 先进行基础分析
        analysis = self.analyze_file_group(file_paths)

        if not self.ai_client:
            return analysis

        try:
            # 准备AI分析数据
            files_info = self._prepare_ai_files_info(analysis.files)

            # 构建AI提示
            prompt = self._build_ai_prompt(files_info, analysis)

            # 调用AI获取响应
            ai_result = await self._call_ai_for_analysis(prompt)

            # 更新分析结果
            self._update_analysis_with_ai_result(analysis, ai_result)

            logfire.info(
                "AI版本分析完成",
                attributes={
                    "file_count": len(file_paths),
                    "recommended": str(analysis.recommended_keep),
                    "confidence": analysis.confidence,
                },
            )

        except Exception as e:
            logfire.error(f"AI版本分析失败: {e}")
            # 保持基础分析结果

        return analysis

    def _collect_file_info(self, file_paths: list[Path]) -> list[FileVersion]:
        """收集文件信息."""
        versions = []
        for path in file_paths:
            try:
                stat = path.stat()
                version = FileVersion(
                    path=path,
                    size=stat.st_size,
                    modified_time=stat.st_mtime,
                    name_pattern=self._extract_name_pattern(path.name),
                    version_indicator=self._extract_version_indicator(path.name),
                )
                versions.append(version)
            except Exception as e:
                logfire.warning(f"无法获取文件信息: {path} - {e}")

        # 按修改时间排序
        versions.sort(key=lambda v: v.modified_time, reverse=True)
        return versions

    def _extract_name_pattern(self, filename: str) -> str:
        """提取文件名模式."""
        # 移除版本号
        pattern = re.sub(r"[_-]?v?\d+(?:\.\d+)?", "", filename, flags=re.IGNORECASE)
        # 移除日期
        pattern = re.sub(r"\d{4}[-_]?\d{2}[-_]?\d{2}", "", pattern)
        # 移除括号内容
        pattern = re.sub(r"\([^)]+\)", "", pattern)
        pattern = re.sub(r"\[[^\]]+\]", "", pattern)
        return pattern.strip()

    def _extract_version_indicator(self, filename: str) -> Optional[str]:
        """提取版本标识."""
        # 查找版本号
        version_match = re.search(r"v?(\d+(?:\.\d+)?)", filename, re.IGNORECASE)
        if version_match:
            return version_match.group(0)

        # 查找特殊标识
        indicators = [
            "final",
            "最终",
            "latest",
            "最新",
            "new",
            "old",
            "备份",
            "backup",
            "copy",
            "副本",
        ]
        for indicator in indicators:
            if indicator in filename.lower():
                return indicator

        # 查找日期
        date_match = re.search(r"(\d{4}[-_]?\d{2}[-_]?\d{2})", filename)
        if date_match:
            return date_match.group(0)

        return None

    def _calculate_name_similarity(self, versions: list[FileVersion]) -> float:
        """计算文件名相似度."""
        if len(versions) < 2:
            return 0.0

        # 获取所有文件名模式
        patterns = [v.name_pattern for v in versions]

        # 计算平均相似度
        total_similarity = 0.0
        comparisons = 0

        for i in range(len(patterns)):
            for j in range(i + 1, len(patterns)):
                similarity = self._string_similarity(patterns[i], patterns[j])
                total_similarity += similarity
                comparisons += 1

        return total_similarity / comparisons if comparisons > 0 else 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度（简单实现）."""
        if not s1 or not s2:
            return 0.0

        # 转换为小写
        s1, s2 = s1.lower(), s2.lower()

        # 如果完全相同
        if s1 == s2:
            return 1.0

        # 计算公共子串长度
        common_len = 0
        for char in set(s1):
            common_len += min(s1.count(char), s2.count(char))

        # 相似度 = 公共字符数 / 平均长度
        avg_len = (len(s1) + len(s2)) / 2
        return common_len / avg_len if avg_len > 0 else 0.0

    def _identify_version_relation(
        self, versions: list[FileVersion]
    ) -> tuple[bool, Optional[VersionRelation]]:
        """识别版本关系."""
        if len(versions) < 2:
            return False, None

        # 检查是否有明显的版本标识
        has_version_indicators = any(v.version_indicator for v in versions)
        if not has_version_indicators:
            return False, None

        # 按版本分数排序
        sorted_versions = sorted(versions, key=lambda v: v.version_score, reverse=True)

        # 确定基础文件（分数最高的）
        base_file = sorted_versions[0]
        derived_files = sorted_versions[1:]

        # 判断关系类型
        relation_type = "version"  # 默认为版本关系
        confidence = 0.7

        # 检查是否为备份关系
        if any(
            "backup" in str(f.path).lower() or "备份" in str(f.path)
            for f in derived_files
        ):
            relation_type = "backup"
            confidence = 0.9

        # 检查是否为副本关系
        elif any(
            "copy" in str(f.path).lower() or "副本" in str(f.path)
            for f in derived_files
        ):
            relation_type = "copy"
            confidence = 0.85

        # 构建关系
        relation = VersionRelation(
            relation_type=relation_type,
            confidence=confidence,
            base_file=base_file.path,
            derived_files=[f.path for f in derived_files],
            reason=f"基于文件名模式和修改时间判断为{relation_type}关系",
        )

        return True, relation

    def _prepare_ai_files_info(self, files: list[FileVersion]) -> list[dict[str, Any]]:
        """准备AI分析所需的文件信息."""
        files_info = []
        for fv in files:
            info = {
                "name": fv.path.name,
                "size": fv.size,
                "modified": fv.modified_datetime.isoformat(),
                "version_indicator": fv.version_indicator or "无",
            }
            # 如果可能，读取文件开头
            if fv.path.suffix in [".txt", ".md", ".json", ".yml", ".yaml"]:
                try:
                    with open(fv.path, encoding="utf-8") as f:
                        info["preview"] = f.read(200)
                except Exception:
                    pass
            files_info.append(info)
        return files_info

    def _build_ai_prompt(
        self, files_info: list[dict[str, Any]], analysis: VersionAnalysis
    ) -> str:
        """构建AI分析提示."""
        return prompt_manager.format(
            "version_analysis",
            files=files_info,
            basic_analysis={
                "similarity": analysis.similarity_score,
                "has_relation": analysis.has_version_relation,
                "relation_type": (
                    analysis.relation.relation_type if analysis.relation else None
                ),
            },
        )

    async def _call_ai_for_analysis(self, prompt: str) -> dict[str, Any]:
        """调用AI进行分析."""
        messages = [DeepSeekMessage(role="user", content=prompt)]
        if not self.ai_client:
            return {}

        response = await self.ai_client.chat_completion(
            messages,
            temperature=0.3,  # 降低温度以获得更一致的分析
        )

        # 解析AI响应
        import json

        try:
            # 响应可能直接包含analysis字段，或者需要从content中解析
            if hasattr(response, "content"):
                response_data = json.loads(response.content)
            elif isinstance(response, dict):
                response_data = response
            else:
                # 如果响应类型不符合预期，返回空字典
                return {}

            # 确保response_data是字典类型
            if not isinstance(response_data, dict):
                return {}

            # 获取analysis字段，确保返回dict类型
            analysis_data = response_data.get("analysis", {})
            # 确保返回值是dict[str, Any]类型
            if isinstance(analysis_data, dict):
                return analysis_data
            else:
                return {}

        except (json.JSONDecodeError, AttributeError):
            # 如果AI返回的不是JSON，就使用默认值
            return {}

    def _update_analysis_with_ai_result(
        self, analysis: VersionAnalysis, ai_result: dict[str, Any]
    ) -> None:
        """使用AI结果更新分析."""
        # 更新推荐文件
        if ai_result.get("recommended_file"):
            for fv in analysis.files:
                if fv.path.name == ai_result["recommended_file"]:
                    analysis.recommended_keep = fv.path
                    break

        # 设置AI建议和置信度
        analysis.ai_suggestion = ai_result.get("reason", None)
        if ai_result.get("confidence") is not None:
            analysis.confidence = float(ai_result["confidence"])

    def _generate_basic_recommendation(self, versions: list[FileVersion]) -> Path:
        """生成基础推荐."""
        # 按版本分数排序，选择分数最高的
        sorted_versions = sorted(versions, key=lambda v: v.version_score, reverse=True)
        return sorted_versions[0].path

    def format_analysis_result(self, analysis: VersionAnalysis) -> str:
        """格式化分析结果为友好的展示文本."""
        lines = []

        if analysis.has_version_relation and analysis.relation:
            lines.append(f"📊 版本关系: {analysis.relation.relation_type}")
            lines.append(f"   基础文件: {analysis.relation.base_file.name}")
            lines.append(f"   相关文件: {len(analysis.relation.derived_files)} 个")
            lines.append(f"   置信度: {analysis.relation.confidence:.0%}")
            lines.append("")

        # 格式化推荐保留的文件名
        recommended_file = (
            analysis.recommended_keep.name if analysis.recommended_keep else "无"
        )
        lines.append(f"💡 AI 建议保留: {recommended_file}")
        if analysis.ai_suggestion:
            lines.append(f"   理由: {analysis.ai_suggestion}")
        lines.append(f"   置信度: {analysis.confidence:.0%}")

        return "\n".join(lines)
