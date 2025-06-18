"""测试版本分析器的AI功能."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simple_tools.ai.config import AIConfig
from simple_tools.ai.version_analyzer import (
    VersionAnalyzer,
)


class TestVersionAnalyzerAI:
    """测试版本分析器的AI功能."""

    @pytest.fixture
    def mock_ai_client(self) -> MagicMock:
        """创建模拟的AI客户端."""
        client = MagicMock()
        client.chat_completion = AsyncMock()
        return client

    @pytest.fixture
    def analyzer_with_ai(self, mock_ai_client: MagicMock) -> VersionAnalyzer:
        """创建带AI客户端的分析器."""
        with patch(
            "simple_tools.ai.version_analyzer.DeepSeekClient",
            return_value=mock_ai_client,
        ):
            config = AIConfig(enabled=True, api_key="test-key")
            analyzer = VersionAnalyzer(config)
            analyzer.ai_client = mock_ai_client
            return analyzer

    @pytest.mark.asyncio
    async def test_analyze_with_ai_success(
        self,
        analyzer_with_ai: VersionAnalyzer,
        mock_ai_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试使用AI分析成功的情况."""
        # 创建测试文件
        files = []
        for i in range(3):
            file_path = tmp_path / f"report_v{i}.txt"
            file_path.write_text(f"Version {i} content")
            files.append(file_path)

        # 设置AI响应 - 需要包含analysis字段
        mock_ai_client.chat_completion.return_value = {
            "analysis": {
                "recommended_file": "report_v2.txt",
                "confidence": 0.85,
                "reason": "v2是最新版本，内容最完整",
            }
        }

        # 执行分析
        result = await analyzer_with_ai.analyze_with_ai(files)

        # 验证结果
        assert result.recommended_keep.name == "report_v2.txt"
        assert result.confidence == 0.85  # AI返回的confidence
        assert result.ai_suggestion == "v2是最新版本，内容最完整"

        # 验证AI被调用
        mock_ai_client.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_with_ai_with_preview(
        self,
        analyzer_with_ai: VersionAnalyzer,
        mock_ai_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试AI分析包含文件预览."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("这是一个测试文档的内容" * 20)  # 创建较长内容

        # Mock prompt_manager
        with patch(
            "simple_tools.ai.version_analyzer.prompt_manager"
        ) as mock_prompt_manager:
            mock_prompt_manager.format.return_value = "formatted prompt"

            # 设置AI响应
            ai_response = {
                "analysis": {
                    "recommended_file": "test.txt",
                    "confidence": 0.9,
                    "reason": "文件内容完整",
                }
            }
            mock_ai_client.chat_completion.return_value = ai_response

            # 执行分析
            await analyzer_with_ai.analyze_with_ai([test_file])

            # 验证prompt_manager被调用
            mock_prompt_manager.format.assert_called_once()
            call_args = mock_prompt_manager.format.call_args

            # 验证文件信息中包含预览
            files_info = call_args.kwargs["files"]
            assert len(files_info) == 1
            assert "preview" in files_info[0]
            assert len(files_info[0]["preview"]) == 200  # 只读取前200个字符

    @pytest.mark.asyncio
    async def test_analyze_with_ai_read_error(
        self,
        analyzer_with_ai: VersionAnalyzer,
        mock_ai_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试读取文件预览失败的情况."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Mock文件读取失败
        with patch("builtins.open", side_effect=Exception("Read error")):
            with patch(
                "simple_tools.ai.version_analyzer.prompt_manager"
            ) as mock_prompt_manager:
                mock_prompt_manager.format.return_value = "formatted prompt"

                ai_response = {
                    "analysis": {
                        "recommended_file": "test.txt",
                        "confidence": 0.7,
                        "reason": "基于文件名判断",
                    }
                }
                mock_ai_client.chat_completion.return_value = ai_response

                # 执行分析
                result = await analyzer_with_ai.analyze_with_ai([test_file])

                # 验证即使读取失败也能继续分析
                assert result.recommended_keep.name == "test.txt"

                # 验证文件信息中不包含预览
                files_info = mock_prompt_manager.format.call_args.kwargs["files"]
                assert "preview" not in files_info[0]

    @pytest.mark.asyncio
    async def test_analyze_with_ai_exception(
        self,
        analyzer_with_ai: VersionAnalyzer,
        mock_ai_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试AI分析出现异常的情况."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # 设置AI调用失败
        mock_ai_client.chat_completion.side_effect = Exception("API error")

        # 执行分析
        result = await analyzer_with_ai.analyze_with_ai([test_file])

        # 验证返回基础分析结果
        assert result.ai_suggestion is None  # 没有AI建议
        assert result.recommended_keep is not None  # 但有基础推荐
        assert result.confidence == 0.5  # 使用基础置信度

    @pytest.mark.asyncio
    async def test_analyze_with_ai_no_recommended_file(
        self,
        analyzer_with_ai: VersionAnalyzer,
        mock_ai_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试AI没有推荐文件的情况."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # AI响应中没有recommended_file
        mock_ai_client.chat_completion.return_value = {
            "analysis": {"confidence": 0.5, "reason": "无法确定最佳版本"}
        }

        # 执行分析
        result = await analyzer_with_ai.analyze_with_ai([test_file])

        # 验证使用基础推荐
        assert result.recommended_keep.name == "test.txt"  # 使用基础推荐
        assert result.ai_suggestion == "无法确定最佳版本"

    @pytest.mark.asyncio
    async def test_analyze_with_ai_binary_file(
        self,
        analyzer_with_ai: VersionAnalyzer,
        mock_ai_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试分析二进制文件（不尝试读取内容）."""
        # 创建不同类型的文件
        text_file = tmp_path / "doc.txt"
        text_file.write_text("text content")

        binary_file = tmp_path / "image.jpg"
        binary_file.write_bytes(b"\xff\xd8\xff\xe0")  # JPEG header

        excel_file = tmp_path / "data.xlsx"
        excel_file.write_bytes(b"PK")  # ZIP header

        with patch(
            "simple_tools.ai.version_analyzer.prompt_manager"
        ) as mock_prompt_manager:
            mock_prompt_manager.format.return_value = "formatted prompt"

            ai_response = {
                "analysis": {
                    "recommended_file": "doc.txt",
                    "confidence": 0.8,
                    "reason": "文本文件更可能是主版本",
                }
            }
            mock_ai_client.chat_completion.return_value = ai_response

            # 执行分析
            await analyzer_with_ai.analyze_with_ai([text_file, binary_file, excel_file])

            # 验证只有文本文件有预览
            # format 方法的第一个参数是模板名，后面是关键字参数
            files_info = mock_prompt_manager.format.call_args.kwargs["files"]
            assert len(files_info) == 3

            # 检查哪些文件有预览
            for info in files_info:
                if info["name"] == "doc.txt":
                    assert "preview" in info
                else:
                    assert "preview" not in info

    def test_extract_version_indicator_more_cases(self) -> None:
        """测试更多版本标识提取的情况."""
        analyzer = VersionAnalyzer()

        # 测试更多模式
        assert (
            analyzer._extract_version_indicator("file_v2.5.1.txt") == "v2.5"
        )  # 只匹配到第一个小数点
        assert analyzer._extract_version_indicator("report_2024.doc") == "2024"
        assert analyzer._extract_version_indicator("最新版本.txt") == "最新"
        assert analyzer._extract_version_indicator("old_backup.txt") == "old"
        assert analyzer._extract_version_indicator("document_副本.txt") == "副本"
        assert (
            analyzer._extract_version_indicator("file_FINAL_v2.txt") == "v2"
        )  # v2优先于final
        assert (
            analyzer._extract_version_indicator("report-2024-12-25.pdf") == "2024"
        )  # 数字优先
        assert (
            analyzer._extract_version_indicator("plain_file.txt") is None
        )  # 无版本标识

    def test_string_similarity_edge_cases(self) -> None:
        """测试字符串相似度计算的边界情况."""
        analyzer = VersionAnalyzer()

        # 空字符串
        assert analyzer._string_similarity("", "") == 0.0
        assert analyzer._string_similarity("test", "") == 0.0
        assert analyzer._string_similarity("", "test") == 0.0

        # 大小写
        assert analyzer._string_similarity("TEST", "test") == 1.0

        # 部分重叠
        assert analyzer._string_similarity("abc", "abd") > 0.5
        assert analyzer._string_similarity("abc", "xyz") < 0.5

    def test_collect_file_info_with_errors(self, tmp_path: Path) -> None:
        """测试收集文件信息时的错误处理."""
        analyzer = VersionAnalyzer()

        # 创建一个正常文件
        good_file = tmp_path / "good.txt"
        good_file.write_text("content")

        # 创建一个不存在的文件路径
        bad_file = tmp_path / "nonexistent.txt"

        # 使用patch来mock stat方法
        def mock_stat_side_effect(path_instance: Path) -> Any:
            """Mock stat 方法的副作用函数."""
            if path_instance == good_file:
                stat_result = MagicMock()
                stat_result.st_size = 100
                stat_result.st_mtime = 1234567890
                return stat_result
            else:
                raise FileNotFoundError("File not found")

        # 创建一个 mock 函数来替换 stat 方法
        def mock_stat_method(path_self: Path, *, follow_symlinks: bool = True) -> Any:
            return mock_stat_side_effect(path_self)

        # 使用patch来模拟stat方法
        with patch.object(Path, "stat", mock_stat_method):
            # 执行收集
            result = analyzer._collect_file_info([good_file, bad_file])

            # 验证只返回成功的文件
            assert len(result) == 1
            assert result[0].path == good_file
