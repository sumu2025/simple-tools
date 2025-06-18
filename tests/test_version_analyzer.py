"""测试文件版本分析器功能."""

from pathlib import Path

import pytest

from simple_tools.ai.config import AIConfig
from simple_tools.ai.version_analyzer import (
    FileVersion,
    VersionAnalysis,
    VersionAnalyzer,
    VersionRelation,
)


class TestFileVersion:
    """测试FileVersion模型."""

    def test_version_score_calculation(self) -> None:
        """测试版本评分计算."""
        # 测试final版本得分最高
        final_version = FileVersion(
            path=Path("report_final.doc"),
            size=1024,
            modified_time=1000000000,
            version_indicator="final",
        )
        assert final_version.version_score > 1.0

        # 测试带版本号的文件
        v2_version = FileVersion(
            path=Path("report_v2.doc"),
            size=1024,
            modified_time=1000000000,
            version_indicator="v2",
        )
        assert v2_version.version_score > 0

        # 测试备份文件得分较低
        backup_version = FileVersion(
            path=Path("report_backup.doc"),
            size=1024,
            modified_time=1000000000,
            version_indicator="backup",
        )
        assert backup_version.version_score < v2_version.version_score


class TestVersionAnalyzer:
    """测试版本分析器."""

    def test_extract_version_indicator(self) -> None:
        """测试版本标识提取."""
        analyzer = VersionAnalyzer()

        # 测试版本号提取
        assert analyzer._extract_version_indicator("document_v1.txt") == "v1"
        assert analyzer._extract_version_indicator("report_V2.5.doc") == "V2.5"
        assert analyzer._extract_version_indicator("file_2024_12_25.txt") == "2024"

        # 测试特殊标识
        assert analyzer._extract_version_indicator("report_final.doc") == "final"
        assert analyzer._extract_version_indicator("backup_data.txt") == "backup"

    def test_string_similarity(self) -> None:
        """测试字符串相似度计算."""
        analyzer = VersionAnalyzer()

        # 完全相同
        assert analyzer._string_similarity("test", "test") == 1.0

        # 部分相似
        similarity = analyzer._string_similarity("report_v1", "report_v2")
        assert 0.5 < similarity < 1.0

        # 完全不同
        similarity = analyzer._string_similarity("abc", "xyz")
        assert similarity < 0.5

    def test_analyze_file_group_basic(self, tmp_path: Path) -> None:
        """测试基础文件组分析."""
        # 创建测试文件
        files = []
        for i in range(1, 4):
            file_path = tmp_path / f"report_v{i}.txt"
            file_path.write_text(f"Version {i}")
            files.append(file_path)

        # 执行分析
        analyzer = VersionAnalyzer()
        analysis = analyzer.analyze_file_group(files)

        assert isinstance(analysis, VersionAnalysis)
        assert len(analysis.files) == 3
        assert analysis.has_version_relation
        assert analysis.recommended_keep is not None

    def test_identify_version_relation(self, tmp_path: Path) -> None:
        """测试版本关系识别."""
        # 创建有版本关系的文件
        v1 = tmp_path / "doc_v1.txt"
        v2 = tmp_path / "doc_v2.txt"
        final = tmp_path / "doc_final.txt"

        for f in [v1, v2, final]:
            f.write_text("content")

        analyzer = VersionAnalyzer()
        file_versions = analyzer._collect_file_info([v1, v2, final])
        has_relation, relation = analyzer._identify_version_relation(file_versions)

        assert has_relation
        assert relation is not None
        assert relation.relation_type == "version"
        assert relation.confidence > 0.5

    def test_format_analysis_result(self) -> None:
        """测试分析结果格式化."""
        analyzer = VersionAnalyzer()

        # 创建模拟分析结果
        analysis = VersionAnalysis(
            files=[],
            similarity_score=0.8,
            has_version_relation=True,
            relation=VersionRelation(
                relation_type="version",
                confidence=0.9,
                base_file=Path("report_final.doc"),
                derived_files=[Path("report_v1.doc"), Path("report_v2.doc")],
                reason="基于文件名和修改时间判断",
            ),
            recommended_keep=Path("report_final.doc"),
            confidence=0.85,
        )

        formatted = analyzer.format_analysis_result(analysis)
        assert "版本关系: version" in formatted
        assert "基础文件: report_final.doc" in formatted
        assert "置信度: 90%" in formatted

    @pytest.mark.asyncio
    async def test_analyze_with_ai_no_client(self, tmp_path: Path) -> None:
        """测试无AI客户端时的分析."""
        # 创建测试文件
        files = [tmp_path / f"file{i}.txt" for i in range(3)]
        for f in files:
            f.write_text("content")

        # 不提供API密钥
        config = AIConfig(enabled=False)
        analyzer = VersionAnalyzer(config)

        # 应该回退到基础分析
        analysis = await analyzer.analyze_with_ai(files)
        assert isinstance(analysis, VersionAnalysis)
        assert analysis.ai_suggestion is None  # 没有AI建议


class TestIntegration:
    """集成测试."""

    def test_complete_workflow(self, tmp_path: Path) -> None:
        """测试完整工作流程."""
        # 创建一组有版本关系的文件
        base_content = "这是一个测试文档"

        # v1 - 最早的版本
        v1 = tmp_path / "project_plan_v1.doc"
        v1.write_text(base_content)

        # v2 - 中间版本
        v2 = tmp_path / "project_plan_v2.doc"
        v2.write_text(base_content + "\n添加了新内容")

        # final - 最终版本
        final = tmp_path / "project_plan_final.doc"
        final.write_text(base_content + "\n添加了新内容\n最终确定版本")

        # backup - 备份
        backup = tmp_path / "project_plan_backup.doc"
        backup.write_text(base_content)

        # 执行分析
        analyzer = VersionAnalyzer()
        analysis = analyzer.analyze_file_group([v1, v2, final, backup])

        # 验证结果
        assert analysis.has_version_relation
        assert analysis.recommended_keep.name == "project_plan_final.doc"
        assert analysis.confidence > 0.5

        # 验证关系识别
        assert analysis.relation is not None
        assert analysis.relation.base_file.name == "project_plan_final.doc"
        assert len(analysis.relation.derived_files) == 3
