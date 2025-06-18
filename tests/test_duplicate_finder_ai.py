"""测试duplicate_finder的AI功能和错误处理."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from simple_tools.ai.config import AIConfig
from simple_tools.cli import cli
from simple_tools.core.duplicate_finder import (
    DuplicateConfig,
    DuplicateFinder,
    DuplicateGroup,
    _perform_ai_analysis,
)


@pytest.fixture
def runner() -> CliRunner:
    """创建命令行测试运行器."""
    return CliRunner()


class TestDuplicateFinderErrors:
    """测试duplicate_finder的错误处理."""

    def test_calculate_file_hash_permission_error(self, tmp_path: Path) -> None:
        """测试计算文件哈希时的权限错误."""
        config = DuplicateConfig(path=str(tmp_path))
        finder = DuplicateFinder(config)

        # 创建一个文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # 模拟权限错误
        with patch("builtins.open", side_effect=PermissionError("No permission")):
            with pytest.raises(Exception) as exc_info:
                finder._calculate_file_hash(test_file)
            # 检查是否包含预期的错误信息
            assert "无法读取文件" in str(exc_info.value)

    def test_calculate_file_hash_file_not_found(self, tmp_path: Path) -> None:
        """测试计算文件哈希时文件不存在."""
        config = DuplicateConfig(path=str(tmp_path))
        finder = DuplicateFinder(config)

        # 不存在的文件
        test_file = tmp_path / "nonexistent.txt"

        # 模拟文件不存在错误
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(Exception) as exc_info:
                finder._calculate_file_hash(test_file)
            assert "文件不存在" in str(exc_info.value)

    def test_calculate_file_hash_os_error(self, tmp_path: Path) -> None:
        """测试计算文件哈希时的系统错误."""
        config = DuplicateConfig(path=str(tmp_path))
        finder = DuplicateFinder(config)

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # 模拟OSError
        with patch("builtins.open", side_effect=OSError("Disk error")):
            with pytest.raises(Exception) as exc_info:
                finder._calculate_file_hash(test_file)
            assert "读取文件失败" in str(exc_info.value)

    def test_calculate_file_hash_general_error(self, tmp_path: Path) -> None:
        """测试计算文件哈希时的一般错误."""
        config = DuplicateConfig(path=str(tmp_path))
        finder = DuplicateFinder(config)

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # 模拟其他异常
        with patch("builtins.open", side_effect=Exception("Unknown error")):
            with pytest.raises(Exception) as exc_info:
                finder._calculate_file_hash(test_file)
            assert "计算文件哈希失败" in str(exc_info.value)

    def test_scan_files_directory_permission_error(self, tmp_path: Path) -> None:
        """测试扫描目录时的权限错误."""
        config = DuplicateConfig(path=str(tmp_path))
        finder = DuplicateFinder(config)

        # 模拟权限错误
        with patch("pathlib.Path.glob", side_effect=PermissionError("No permission")):
            with pytest.raises(Exception) as exc_info:
                finder._scan_files()
            assert "无权限访问目录" in str(exc_info.value)

    def test_scan_files_os_error(self, tmp_path: Path) -> None:
        """测试扫描目录时的系统错误."""
        config = DuplicateConfig(path=str(tmp_path))
        finder = DuplicateFinder(config)

        # 模拟OSError
        with patch("pathlib.Path.glob", side_effect=OSError("System error")):
            with pytest.raises(Exception) as exc_info:
                finder._scan_files()
            assert "扫描目录失败" in str(exc_info.value)


class TestDuplicateFinderAI:
    """测试duplicate_finder的AI功能."""

    @pytest.mark.asyncio
    async def test_perform_ai_analysis_success(self) -> None:
        """测试AI分析成功的情况."""
        # 创建测试数据
        duplicate_groups = [
            DuplicateGroup(
                hash="abc123",
                size=1024,
                count=2,
                files=[Path("file1.txt"), Path("file2.txt")],
                potential_save=1024,
            )
        ]

        # 模拟AI配置
        ai_config = MagicMock(spec=AIConfig)
        ai_config.enabled = True

        # 模拟VersionAnalyzer
        with patch(
            "simple_tools.core.duplicate_finder.VersionAnalyzer"
        ) as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer

            # 模拟analyze_with_ai返回值
            mock_analysis = MagicMock()
            mock_analysis.recommended_keep = Path("file1.txt")
            mock_analysis.confidence = 0.9
            mock_analyzer.analyze_with_ai = AsyncMock(return_value=mock_analysis)

            # 模拟format_analysis_result
            mock_analyzer.format_analysis_result.return_value = "AI分析结果文本"

            # 执行测试
            result = await _perform_ai_analysis(duplicate_groups, ai_config)

            # 验证结果
            assert "abc123" in result
            assert result["abc123"] == "AI分析结果文本"
            assert "abc123_data" in result
            assert result["abc123_data"]["recommended_keep"] == Path("file1.txt")
            assert result["abc123_data"]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_perform_ai_analysis_with_error(self) -> None:
        """测试AI分析出错的情况."""
        # 创建测试数据
        duplicate_groups = [
            DuplicateGroup(
                hash="abc123",
                size=1024,
                count=2,
                files=[Path("file1.txt"), Path("file2.txt")],
                potential_save=1024,
            )
        ]

        ai_config = MagicMock(spec=AIConfig)
        ai_config.enabled = True

        # 模拟VersionAnalyzer抛出异常
        with patch(
            "simple_tools.core.duplicate_finder.VersionAnalyzer"
        ) as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_with_ai = AsyncMock(side_effect=Exception("AI error"))

            # 执行测试
            result = await _perform_ai_analysis(duplicate_groups, ai_config)

            # 验证结果为空（错误被捕获）
            assert result == {}

    def test_duplicates_cmd_with_ai_analyze(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """测试带--ai-analyze参数的duplicates命令."""
        # 创建测试文件
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        # Mock必要的组件
        with patch(
            "simple_tools.core.duplicate_finder.DuplicateFinder"
        ) as mock_finder_class:
            # 设置finder的模拟
            mock_finder = MagicMock()
            mock_finder_class.return_value = mock_finder

            # 模拟find_duplicates返回重复文件组
            duplicate_group = DuplicateGroup(
                hash="abc123",
                size=7,
                count=2,
                files=[tmp_path / "file1.txt", tmp_path / "file2.txt"],
                potential_save=7,
            )
            mock_finder.find_duplicates.return_value = [duplicate_group]
            mock_finder._scan_files.return_value = [MagicMock(), MagicMock()]

            # Mock AI配置
            with patch(
                "simple_tools.core.duplicate_finder.AIConfig"
            ) as mock_ai_config_class:
                mock_ai_config = MagicMock()
                mock_ai_config.enabled = True
                mock_ai_config_class.return_value = mock_ai_config

                # Mock asyncio.run
                with patch(
                    "simple_tools.core.duplicate_finder.asyncio.run"
                ) as mock_asyncio_run:
                    mock_asyncio_run.return_value = {
                        "abc123": "AI分析结果",
                        "abc123_data": {
                            "recommended_keep": str(tmp_path / "file1.txt"),
                            "confidence": 0.9,
                        },
                    }

                    # 执行命令
                    result = runner.invoke(
                        cli, ["duplicates", str(tmp_path), "--ai-analyze"]
                    )

                    # 验证输出
                    assert result.exit_code == 0
                    assert "正在进行AI版本分析" in result.output
                    assert "AI分析完成" in result.output
                    assert "AI分析结果" in result.output

    def test_duplicates_cmd_ai_disabled(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """测试AI未启用时的处理."""
        # 创建测试文件
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        with patch(
            "simple_tools.core.duplicate_finder.DuplicateFinder"
        ) as mock_finder_class:
            mock_finder = MagicMock()
            mock_finder_class.return_value = mock_finder

            duplicate_group = DuplicateGroup(
                hash="abc123",
                size=7,
                count=2,
                files=[tmp_path / "file1.txt", tmp_path / "file2.txt"],
                potential_save=7,
            )
            mock_finder.find_duplicates.return_value = [duplicate_group]
            mock_finder._scan_files.return_value = [MagicMock(), MagicMock()]

            # Mock AI配置为未启用
            with patch(
                "simple_tools.core.duplicate_finder.AIConfig"
            ) as mock_ai_config_class:
                mock_ai_config = MagicMock()
                mock_ai_config.enabled = False
                mock_ai_config_class.return_value = mock_ai_config

                # 执行命令
                result = runner.invoke(
                    cli, ["duplicates", str(tmp_path), "--ai-analyze"]
                )

                assert result.exit_code == 0
                assert "AI功能未启用" in result.output

    def test_duplicates_cmd_json_format_with_ai(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """测试JSON格式输出包含AI分析结果."""
        # 创建测试文件
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        with patch(
            "simple_tools.core.duplicate_finder.DuplicateFinder"
        ) as mock_finder_class:
            mock_finder = MagicMock()
            mock_finder_class.return_value = mock_finder

            duplicate_group = DuplicateGroup(
                hash="abc123",
                size=7,
                count=2,
                files=[tmp_path / "file1.txt", tmp_path / "file2.txt"],
                potential_save=7,
            )
            mock_finder.find_duplicates.return_value = [duplicate_group]
            mock_finder._scan_files.return_value = [MagicMock(), MagicMock()]

            # Mock AI分析结果
            with patch(
                "simple_tools.core.duplicate_finder.AIConfig"
            ) as mock_ai_config_class:
                mock_ai_config = MagicMock()
                mock_ai_config.enabled = True
                mock_ai_config_class.return_value = mock_ai_config

                with patch(
                    "simple_tools.core.duplicate_finder.asyncio.run"
                ) as mock_asyncio_run:
                    mock_asyncio_run.return_value = {
                        "abc123": "AI分析结果",
                        "abc123_data": {
                            "recommended_keep": str(tmp_path / "file1.txt"),
                            "confidence": 0.9,
                        },
                    }

                    # 执行命令
                    result = runner.invoke(
                        cli,
                        [
                            "duplicates",
                            str(tmp_path),
                            "--ai-analyze",
                            "--format",
                            "json",
                        ],
                    )

                    assert result.exit_code == 0
                    # 验证JSON输出 - 只获取JSON部分
                    output_lines = result.output.strip().split("\n")
                    # 找到JSON开始的位置（以{开头的行）
                    json_start = 0
                    for i, line in enumerate(output_lines):
                        if line.strip().startswith("{"):
                            json_start = i
                            break
                    # 从JSON开始位置提取JSON内容
                    json_content = "\n".join(output_lines[json_start:])
                    output_data = json.loads(json_content)
                    assert "groups" in output_data
                    assert len(output_data["groups"]) == 1
                    assert "ai_recommendation" in output_data["groups"][0]
                    assert "ai_confidence" in output_data["groups"][0]
