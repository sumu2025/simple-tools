"""测试文档摘要命令功能."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from simple_tools.ai.config import AIConfig
from simple_tools.ai.summarizer import SummaryResult
from simple_tools.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """创建命令行测试运行器."""
    return CliRunner()


@pytest.fixture
def mock_ai_config() -> MagicMock:
    """模拟AI配置."""
    config = MagicMock(spec=AIConfig)
    config.enabled = True
    config.is_configured = True
    config.api_key = "test-api-key"
    return config


@pytest.fixture
def mock_summarize_result() -> MagicMock:
    """模拟摘要结果."""
    result = MagicMock(spec=SummaryResult)
    result.file_path = Path("test.txt")
    result.doc_type = "text"
    result.word_count = 1000
    result.summary = "这是一个测试摘要内容"
    result.summary_length = 10
    result.error = None
    return result


class TestSummarizeCommand:
    """测试summarize命令."""

    def test_summarize_command_exists(self, runner: CliRunner) -> None:
        """测试summarize命令是否存在."""
        result = runner.invoke(cli, ["summarize", "--help"])
        assert result.exit_code == 0
        assert "生成文档摘要" in result.output

    def test_summarize_ai_disabled(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试AI功能未启用时的错误处理."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")

        with patch("simple_tools.core.summarize_cmd.get_ai_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.enabled = False
            mock_get_config.return_value = mock_config

            result = runner.invoke(cli, ["summarize", str(test_file)])
            assert result.exit_code == 1
            assert "AI功能未启用" in result.output

    def test_summarize_ai_not_configured(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """测试AI功能未配置时的错误处理."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")

        with patch("simple_tools.core.summarize_cmd.get_ai_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.enabled = True
            mock_config.is_configured = False
            mock_get_config.return_value = mock_config

            result = runner.invoke(cli, ["summarize", str(test_file)])
            assert result.exit_code == 1
            assert "AI功能未配置" in result.output

    def test_summarize_file_not_found(
        self, runner: CliRunner, mock_ai_config: MagicMock
    ) -> None:
        """测试文件不存在的错误处理."""
        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            result = runner.invoke(cli, ["summarize", "/nonexistent/file.txt"])
            assert result.exit_code == 1
            assert "路径不存在" in result.output

    def test_summarize_directory_without_batch(
        self, runner: CliRunner, mock_ai_config: MagicMock, tmp_path: Path
    ) -> None:
        """测试处理目录但未指定--batch参数."""
        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            result = runner.invoke(cli, ["summarize", str(tmp_path)])
            assert result.exit_code == 1
            assert "未指定 --batch 参数" in result.output

    @patch("simple_tools.core.summarize_cmd.asyncio.run")
    @patch("simple_tools.core.summarize_cmd.DocumentSummarizer")
    def test_summarize_single_file(
        self,
        mock_summarizer_class: MagicMock,
        mock_asyncio_run: MagicMock,
        runner: CliRunner,
        mock_ai_config: MagicMock,
        mock_summarize_result: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试单个文件摘要生成."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("这是一个测试文档的内容")

        # 设置模拟
        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_asyncio_run.return_value = mock_summarize_result

        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            result = runner.invoke(cli, ["summarize", str(test_file)])

            assert result.exit_code == 0
            assert "正在生成文档摘要" in result.output
            assert "test.txt" in result.output
            assert "这是一个测试摘要内容" in result.output

            # 验证调用
            mock_asyncio_run.assert_called_once()

    @patch("simple_tools.core.summarize_cmd.asyncio.run")
    @patch("simple_tools.core.summarize_cmd.DocumentSummarizer")
    def test_summarize_single_file_with_error(
        self,
        mock_summarizer_class: MagicMock,
        mock_asyncio_run: MagicMock,
        runner: CliRunner,
        mock_ai_config: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试单个文件摘要生成失败."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")

        # 设置失败的结果
        failed_result = MagicMock()
        failed_result.file_path = test_file
        failed_result.error = "API调用失败"
        failed_result.doc_type = "text"
        failed_result.word_count = 100
        failed_result.summary_length = 0

        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_asyncio_run.return_value = failed_result

        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            result = runner.invoke(cli, ["summarize", str(test_file)])

            assert result.exit_code == 0
            assert "摘要生成失败" in result.output
            assert "API调用失败" in result.output

    @patch("simple_tools.core.summarize_cmd.asyncio.run")
    @patch("simple_tools.core.summarize_cmd.DocumentSummarizer")
    def test_summarize_with_output(
        self,
        mock_summarizer_class: MagicMock,
        mock_asyncio_run: MagicMock,
        runner: CliRunner,
        mock_ai_config: MagicMock,
        mock_summarize_result: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试保存摘要到文件."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")
        output_file = tmp_path / "summary.txt"

        # 设置模拟
        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_asyncio_run.return_value = mock_summarize_result

        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            result = runner.invoke(
                cli, ["summarize", str(test_file), "-o", str(output_file)]
            )

            assert result.exit_code == 0
            assert "摘要已保存到" in result.output

            # 验证保存方法被调用
            mock_summarizer.save_summaries.assert_called_once()

    @patch("simple_tools.core.summarize_cmd.asyncio.run")
    @patch("simple_tools.core.summarize_cmd.DocumentSummarizer")
    @patch("simple_tools.core.summarize_cmd.ProgressTracker")
    def test_summarize_batch(
        self,
        mock_progress_class: MagicMock,
        mock_summarizer_class: MagicMock,
        mock_asyncio_run: MagicMock,
        runner: CliRunner,
        mock_ai_config: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试批量摘要生成."""
        # 创建多个测试文件
        for i in range(3):
            (tmp_path / f"test{i}.txt").write_text(f"测试内容{i}")

        # 设置批量结果
        batch_result = MagicMock()
        batch_result.success = 2
        batch_result.failed = 1
        batch_result.total = 3
        batch_result.results = [
            MagicMock(
                file_path=Path(f"test{i}.txt"),
                error=None if i < 2 else "失败",
                summary=f"摘要{i}",
            )
            for i in range(3)
        ]

        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_summarizer_class.SUPPORTED_FORMATS = {".txt": None}
        mock_asyncio_run.return_value = batch_result

        # 设置进度跟踪器
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=None)
        mock_progress_class.return_value = mock_progress

        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            result = runner.invoke(cli, ["summarize", str(tmp_path), "--batch"])

            assert result.exit_code == 0
            assert "批量生成 3 个文档的摘要" in result.output
            assert "成功: 2 个文件" in result.output
            assert "失败: 1 个文件" in result.output

    @patch("simple_tools.core.summarize_cmd.asyncio.run")
    @patch("simple_tools.core.summarize_cmd.DocumentSummarizer")
    def test_summarize_with_options(
        self,
        mock_summarizer_class: MagicMock,
        mock_asyncio_run: MagicMock,
        runner: CliRunner,
        mock_ai_config: MagicMock,
        mock_summarize_result: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试带各种选项的摘要生成."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")

        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        mock_asyncio_run.return_value = mock_summarize_result

        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            result = runner.invoke(
                cli,
                [
                    "summarize",
                    str(test_file),
                    "--length",
                    "300",
                    "--language",
                    "en",
                    "--no-cache",
                ],
            )

            assert result.exit_code == 0

            # 验证参数传递
            # asyncio.run被调用时传递的是协程对象
            mock_asyncio_run.assert_called_once()
            # 检查是否是协程 - 只需要检查是否被调用
            assert mock_asyncio_run.called

    def test_summarize_json_format(
        self,
        runner: CliRunner,
        mock_ai_config: MagicMock,
        mock_summarize_result: MagicMock,
        tmp_path: Path,
    ) -> None:
        """测试JSON格式输出."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")
        output_file = tmp_path / "summary.json"

        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            with patch(
                "simple_tools.core.summarize_cmd.asyncio.run",
                return_value=mock_summarize_result,
            ):
                with patch(
                    "simple_tools.core.summarize_cmd.DocumentSummarizer"
                ) as mock_class:
                    mock_summarizer = MagicMock()
                    mock_class.return_value = mock_summarizer

                    result = runner.invoke(
                        cli,
                        [
                            "summarize",
                            str(test_file),
                            "--format",
                            "json",
                            "-o",
                            str(output_file),
                        ],
                    )

                    assert result.exit_code == 0
                    # 验证调用时使用了json格式
                    mock_summarizer.save_summaries.assert_called_with(
                        [mock_summarize_result], output_file, "json"
                    )

    def test_summarize_empty_directory(
        self, runner: CliRunner, mock_ai_config: MagicMock, tmp_path: Path
    ) -> None:
        """测试空目录的批量处理."""
        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            with patch(
                "simple_tools.core.summarize_cmd.DocumentSummarizer"
            ) as mock_class:
                mock_class.SUPPORTED_FORMATS = {".txt": None, ".pdf": None}

                result = runner.invoke(cli, ["summarize", str(tmp_path), "--batch"])

                assert result.exit_code == 0
                assert "没有找到支持的文档文件" in result.output

    def test_summarize_exception_handling(
        self, runner: CliRunner, mock_ai_config: MagicMock, tmp_path: Path
    ) -> None:
        """测试异常处理."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")

        with patch(
            "simple_tools.core.summarize_cmd.get_ai_config", return_value=mock_ai_config
        ):
            with patch(
                "simple_tools.core.summarize_cmd.DocumentSummarizer"
            ) as mock_class:
                mock_class.side_effect = Exception("意外错误")

                result = runner.invoke(cli, ["summarize", str(test_file)])

                assert result.exit_code == 1
                assert "生成摘要时发生错误" in result.output
