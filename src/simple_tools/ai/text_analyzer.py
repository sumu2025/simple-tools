"""文本替换智能分析器 - 提供替换操作的风险分析和建议."""

import asyncio
import re
from typing import Optional

import logfire
from pydantic import BaseModel, Field

from .config import AIConfig, get_ai_config
from .deepseek_client import DeepSeekClient, DeepSeekResponse


class ReplacePattern(BaseModel):
    """替换模式信息."""

    old_text: str = Field(..., description="要查找的文本")
    new_text: str = Field(..., description="替换后的文本")

    @property
    def pattern(self) -> str:
        """获取完整的替换模式."""
        return f"{self.old_text}:{self.new_text}"


class ReplaceRisk(BaseModel):
    """替换风险信息."""

    level: str = Field(..., description="风险等级: low/medium/high")
    reason: str = Field(..., description="风险原因")
    example: Optional[str] = Field(None, description="可能出错的示例")
    suggestion: Optional[str] = Field(None, description="改进建议")


class ReplaceAnalysis(BaseModel):
    """替换分析结果."""

    pattern: ReplacePattern = Field(..., description="原始替换模式")
    risks: list[ReplaceRisk] = Field(default_factory=list, description="识别的风险")
    improved_pattern: Optional[str] = Field(None, description="改进的替换模式")
    safe_regex: Optional[str] = Field(None, description="安全的正则表达式")
    confidence: float = Field(0.0, description="分析置信度")

    @property
    def risk_level(self) -> str:
        """获取整体风险等级."""
        if not self.risks:
            return "low"

        if any(r.level == "high" for r in self.risks):
            return "high"
        elif any(r.level == "medium" for r in self.risks):
            return "medium"
        else:
            return "low"

    @property
    def has_risks(self) -> bool:
        """是否存在风险."""
        return len(self.risks) > 0


class TextAnalyzer:
    """文本替换智能分析器."""

    def __init__(self, ai_config: Optional[AIConfig] = None):
        """初始化文本分析器."""
        self.ai_config = ai_config or get_ai_config()
        self.client = DeepSeekClient(self.ai_config)

    async def analyze_replace_pattern(
        self,
        old_text: str,
        new_text: str,
        sample_content: Optional[str] = None,
        file_extensions: Optional[list[str]] = None,
    ) -> ReplaceAnalysis:
        """分析替换模式的潜在风险.

        Args:
            old_text: 要查找的文本
            new_text: 替换后的文本
            sample_content: 文件内容样本（用于更准确的分析）
            file_extensions: 文件扩展名列表（如 ['.py', '.js']）

        Returns:
            替换分析结果

        """
        with logfire.span(
            "analyze_replace_pattern",
            attributes={
                "old_text": old_text,
                "new_text": new_text,
                "has_sample": bool(sample_content),
            },
        ):
            pattern = ReplacePattern(old_text=old_text, new_text=new_text)

            if not self.ai_config.enabled:
                return self._basic_analysis(pattern)

            try:
                prompt = self._build_analysis_prompt(
                    pattern, sample_content, file_extensions
                )

                from .deepseek_client import DeepSeekMessage

                messages = [
                    DeepSeekMessage(
                        role="system",
                        content="你是一个文本处理专家，擅长识别文本替换操作中的潜在风险。",
                    ),
                    DeepSeekMessage(role="user", content=prompt),
                ]

                response = await self.client.chat_completion(
                    messages=messages,
                    temperature=0.3,
                )

                return self._parse_analysis_response(pattern, response)

            except Exception as e:
                logfire.error(f"AI分析失败: {e}")
                return self._basic_analysis(pattern)

    def _basic_analysis(self, pattern: ReplacePattern) -> ReplaceAnalysis:
        """基础的替换模式分析（不依赖AI）."""
        risks = []

        if not pattern.new_text:
            risks.append(
                ReplaceRisk(
                    level="medium",
                    reason="替换为空字符串会删除匹配的文本",
                    suggestion="确认是否真的要删除这些文本",
                )
            )

        if pattern.old_text.isalnum():
            common_words_with_substring = {
                "bug": ["debug", "bugfix", "debugger"],
                "test": ["testing", "tested", "contest"],
                "class": ["classname", "classification", "subclass"],
                "log": ["login", "dialog", "catalog"],
                "port": ["import", "export", "support"],
            }

            if pattern.old_text.lower() in common_words_with_substring:
                affected = common_words_with_substring[pattern.old_text.lower()]
                risks.append(
                    ReplaceRisk(
                        level="high",
                        reason=f"'{pattern.old_text}' 是其他常见词的子串",
                        example=f"可能会影响: {', '.join(affected[:3])}",
                        suggestion=f"使用单词边界: \\b{pattern.old_text}\\b",
                    )
                )

        special_chars = set(re.findall(r"[^\w\s]", pattern.old_text))
        if special_chars:
            risks.append(
                ReplaceRisk(
                    level="medium",
                    reason="包含特殊字符，可能需要转义",
                    example=f"特殊字符: {', '.join(special_chars)}",
                    suggestion="考虑使用正则表达式的转义",
                )
            )

        improved_pattern = None
        if pattern.old_text.isalnum() and len(risks) > 0:
            improved_pattern = f"\\b{pattern.old_text}\\b:{pattern.new_text}"

        return ReplaceAnalysis(
            pattern=pattern,
            risks=risks,
            improved_pattern=improved_pattern,
            confidence=0.7,
        )

    def _build_analysis_prompt(
        self,
        pattern: ReplacePattern,
        sample_content: Optional[str],
        file_extensions: Optional[list[str]],
    ) -> str:
        """构建分析prompt."""
        from .prompts import PromptManager

        file_types = ", ".join(file_extensions) if file_extensions else "未知"

        content_samples = (
            (sample_content[:500] + "...")
            if sample_content and len(sample_content) > 500
            else sample_content or "无内容样本"
        )

        base_prompt = PromptManager.format(
            "text_replace_analysis",
            old_text=pattern.old_text,
            new_text=pattern.new_text,
            file_types=file_types,
            content_samples=content_samples,
        )

        format_instructions = """

请严格按照以下JSON格式输出（只返回JSON，不要其他文字）：
{
    "risks": [
        {
            "level": "low/medium/high",
            "reason": "风险原因",
            "example": "可能出错的示例（可选）",
            "suggestion": "改进建议（可选）"
        }
    ],
    "improved_pattern": "改进的替换模式（可选）",
    "safe_regex": "安全的正则表达式（可选）",
    "confidence": 0.0-1.0
}"""

        return base_prompt + format_instructions

    def _parse_analysis_response(
        self, pattern: ReplacePattern, response: DeepSeekResponse
    ) -> ReplaceAnalysis:
        """解析AI响应."""
        try:
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            try:
                import json

                data = json.loads(content)
            except json.JSONDecodeError:
                logfire.warning("无法解析AI响应为JSON")
                return self._basic_analysis(pattern)

            risks = []
            for risk_data in data.get("risks", []):
                risks.append(
                    ReplaceRisk(
                        level=risk_data.get("level", "medium"),
                        reason=risk_data.get("reason", "未知风险"),
                        example=risk_data.get("example"),
                        suggestion=risk_data.get("suggestion"),
                    )
                )

            return ReplaceAnalysis(
                pattern=pattern,
                risks=risks,
                improved_pattern=data.get("improved_pattern"),
                safe_regex=data.get("safe_regex"),
                confidence=data.get("confidence", 0.8),
            )

        except Exception as e:
            logfire.error(f"解析AI响应失败: {e}")
            return self._basic_analysis(pattern)

    def analyze_replace_pattern_sync(
        self,
        old_text: str,
        new_text: str,
        sample_content: Optional[str] = None,
        file_extensions: Optional[list[str]] = None,
    ) -> ReplaceAnalysis:
        """同步版本的分析方法（供CLI使用）."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.analyze_replace_pattern(
                    old_text, new_text, sample_content, file_extensions
                )
            )
        finally:
            loop.close()


def format_risk_display(analysis: ReplaceAnalysis) -> str:
    """格式化风险分析结果的显示."""
    lines = []

    risk_icons = {"low": "✅", "medium": "⚠️", "high": "❌"}

    lines.append("\n📊 AI 文本替换分析")
    lines.append("=" * 50)

    lines.append(f"原始模式: {analysis.pattern.old_text} → {analysis.pattern.new_text}")

    icon = risk_icons[analysis.risk_level]
    lines.append(f"\n{icon} 风险等级: {analysis.risk_level.upper()}")

    if analysis.risks:
        lines.append("\n🔍 识别的风险:")
        for i, risk in enumerate(analysis.risks, 1):
            icon = risk_icons[risk.level]
            lines.append(f"\n  {i}. {icon} {risk.reason}")

            if risk.example:
                lines.append(f"     示例: {risk.example}")

            if risk.suggestion:
                lines.append(f"     建议: {risk.suggestion}")
    else:
        lines.append("\n✅ 未发现明显风险")

    if analysis.improved_pattern:
        lines.append(f"\n💡 推荐模式: {analysis.improved_pattern}")

    if analysis.safe_regex:
        lines.append(f"\n🔧 正则表达式: {analysis.safe_regex}")

    lines.append(f"\n📈 分析置信度: {analysis.confidence * 100:.0f}%")

    return "\n".join(lines)
