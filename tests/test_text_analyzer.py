"""文本替换AI分析器的单元测试."""

import pytest

from simple_tools.ai.config import AIConfig
from simple_tools.ai.text_analyzer import (
    ReplaceAnalysis,
    ReplacePattern,
    ReplaceRisk,
    TextAnalyzer,
    format_risk_display,
)


class TestReplacePattern:
    """测试替换模式类."""

    def test_pattern_creation(self) -> None:
        """测试创建替换模式."""
        pattern = ReplacePattern(old_text="bug", new_text="issue")
        assert pattern.old_text == "bug"
        assert pattern.new_text == "issue"
        assert pattern.pattern == "bug:issue"

    def test_empty_replacement(self) -> None:
        """测试空替换."""
        pattern = ReplacePattern(old_text="TODO", new_text="")
        assert pattern.old_text == "TODO"
        assert pattern.new_text == ""
        assert pattern.pattern == "TODO:"


class TestReplaceRisk:
    """测试风险信息类."""

    def test_risk_creation(self) -> None:
        """测试创建风险信息."""
        risk = ReplaceRisk(
            level="high",
            reason="可能影响其他单词",
            example="debug -> deissue",
            suggestion="使用单词边界",
        )
        assert risk.level == "high"
        assert risk.reason == "可能影响其他单词"
        assert risk.example == "debug -> deissue"
        assert risk.suggestion == "使用单词边界"

    def test_optional_fields(self) -> None:
        """测试可选字段."""
        risk = ReplaceRisk(level="low", reason="测试")
        assert risk.level == "low"
        assert risk.reason == "测试"
        assert risk.example is None
        assert risk.suggestion is None


class TestReplaceAnalysis:
    """测试分析结果类."""

    def test_analysis_creation(self) -> None:
        """测试创建分析结果."""
        pattern = ReplacePattern(old_text="test", new_text="prod")
        analysis = ReplaceAnalysis(
            pattern=pattern,
            risks=[],
            confidence=0.8,
        )
        assert analysis.pattern == pattern
        assert analysis.risks == []
        assert analysis.confidence == 0.8
        assert analysis.risk_level == "low"
        assert not analysis.has_risks

    def test_risk_level_calculation(self) -> None:
        """测试风险等级计算."""
        pattern = ReplacePattern(old_text="test", new_text="prod")

        # 无风险
        analysis = ReplaceAnalysis(pattern=pattern, risks=[])
        assert analysis.risk_level == "low"

        # 只有低风险
        analysis = ReplaceAnalysis(
            pattern=pattern,
            risks=[ReplaceRisk(level="low", reason="测试")],
        )
        assert analysis.risk_level == "low"

        # 有中风险
        analysis = ReplaceAnalysis(
            pattern=pattern,
            risks=[
                ReplaceRisk(level="low", reason="测试1"),
                ReplaceRisk(level="medium", reason="测试2"),
            ],
        )
        assert analysis.risk_level == "medium"

        # 有高风险
        analysis = ReplaceAnalysis(
            pattern=pattern,
            risks=[
                ReplaceRisk(level="low", reason="测试1"),
                ReplaceRisk(level="medium", reason="测试2"),
                ReplaceRisk(level="high", reason="测试3"),
            ],
        )
        assert analysis.risk_level == "high"


class TestTextAnalyzer:
    """测试文本分析器."""

    def test_analyzer_creation(self) -> None:
        """测试创建分析器."""
        analyzer = TextAnalyzer()
        assert analyzer.ai_config is not None
        assert analyzer.client is not None

    def test_basic_analysis_empty_replacement(self) -> None:
        """测试基础分析 - 空替换."""
        analyzer = TextAnalyzer()
        pattern = ReplacePattern(old_text="TODO", new_text="")
        analysis = analyzer._basic_analysis(pattern)

        assert analysis.pattern == pattern
        assert len(analysis.risks) > 0
        assert any(r.reason == "替换为空字符串会删除匹配的文本" for r in analysis.risks)

    def test_basic_analysis_substring_risk(self) -> None:
        """测试基础分析 - 子串风险."""
        analyzer = TextAnalyzer()
        pattern = ReplacePattern(old_text="bug", new_text="issue")
        analysis = analyzer._basic_analysis(pattern)

        assert len(analysis.risks) > 0
        high_risk = next((r for r in analysis.risks if r.level == "high"), None)
        assert high_risk is not None
        assert "debug" in high_risk.example
        assert "\\b" in high_risk.suggestion

    def test_basic_analysis_special_chars(self) -> None:
        """测试基础分析 - 特殊字符."""
        analyzer = TextAnalyzer()
        pattern = ReplacePattern(old_text="$price", new_text="$cost")
        analysis = analyzer._basic_analysis(pattern)

        assert len(analysis.risks) > 0
        special_char_risk = next(
            (r for r in analysis.risks if "特殊字符" in r.reason), None
        )
        assert special_char_risk is not None
        assert "$" in special_char_risk.example

    def test_sync_analysis(self) -> None:
        """测试同步分析方法."""
        analyzer = TextAnalyzer()
        analysis = analyzer.analyze_replace_pattern_sync(
            old_text="test",
            new_text="prod",
        )

        assert isinstance(analysis, ReplaceAnalysis)
        assert analysis.pattern.old_text == "test"
        assert analysis.pattern.new_text == "prod"

    @pytest.mark.asyncio
    async def test_async_analysis_no_ai(self) -> None:
        """测试异步分析（AI未启用）."""
        ai_config = AIConfig(enabled=False)  # 禁用AI
        analyzer = TextAnalyzer(ai_config)

        analysis = await analyzer.analyze_replace_pattern(
            old_text="bug",
            new_text="issue",
            sample_content="def debug(): pass",
            file_extensions=[".py"],
        )

        assert isinstance(analysis, ReplaceAnalysis)
        assert len(analysis.risks) > 0  # 应该有基础分析的风险


class TestFormatRiskDisplay:
    """测试风险显示格式化."""

    def test_format_no_risks(self) -> None:
        """测试格式化无风险的结果."""
        pattern = ReplacePattern(old_text="test", new_text="prod")
        analysis = ReplaceAnalysis(pattern=pattern, risks=[], confidence=0.9)

        output = format_risk_display(analysis)
        assert "AI 文本替换分析" in output
        assert "test → prod" in output
        assert "风险等级: LOW" in output
        assert "未发现明显风险" in output
        assert "90%" in output

    def test_format_with_risks(self) -> None:
        """测试格式化有风险的结果."""
        pattern = ReplacePattern(old_text="bug", new_text="issue")
        analysis = ReplaceAnalysis(
            pattern=pattern,
            risks=[
                ReplaceRisk(
                    level="high",
                    reason="可能影响其他单词",
                    example="debug -> deissue",
                    suggestion="使用 \\bbug\\b",
                ),
                ReplaceRisk(
                    level="medium",
                    reason="在代码中常见",
                ),
            ],
            improved_pattern="\\bbug\\b:issue",
            confidence=0.85,
        )

        output = format_risk_display(analysis)
        assert "风险等级: HIGH" in output
        assert "可能影响其他单词" in output
        assert "debug -> deissue" in output
        assert "使用 \\bbug\\b" in output
        assert "推荐模式: \\bbug\\b:issue" in output
        assert "85%" in output


# 集成测试（需要实际的AI配置）
@pytest.mark.integration
class TestTextAnalyzerIntegration:
    """文本分析器集成测试."""

    @pytest.mark.asyncio
    async def test_real_ai_analysis(self) -> None:
        """测试真实的AI分析（需要API密钥）."""
        analyzer = TextAnalyzer()

        # 只有在AI启用时才运行
        if not analyzer.ai_config.enabled:
            pytest.skip("AI未启用")

        analysis = await analyzer.analyze_replace_pattern(
            old_text="class",
            new_text="type",
            sample_content="""
class User:
    def __init__(self):
        self.user_class = "standard"
""",
            file_extensions=[".py"],
        )

        assert isinstance(analysis, ReplaceAnalysis)
        assert analysis.confidence > 0
        # AI应该识别出风险
        assert len(analysis.risks) > 0
