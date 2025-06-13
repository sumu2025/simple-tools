"""测试 text_replace 的智能确认功能."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from simple_tools.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """创建CLI测试运行器."""
    return CliRunner()


@pytest.fixture
def sample_files(tmp_path: Path) -> tuple[Path, list[Path]]:
    """创建测试文件."""
    # 创建包含待替换文本的文件
    file1 = tmp_path / "doc1.txt"
    file1.write_text("This is TODO task. Another TODO here.")

    file2 = tmp_path / "doc2.txt"
    file2.write_text("TODO: Complete this. TODO: Fix that.")

    file3 = tmp_path / "readme.md"
    file3.write_text("# TODO List\n- TODO item 1\n- TODO item 2")

    return tmp_path, [file1, file2, file3]


class TestTextReplaceSmartConfirm:
    """测试文本替换的智能确认功能."""

    def test_smart_confirm_shows_for_execute_mode(
        self, runner: CliRunner, sample_files: tuple[Path, list[Path]]
    ) -> None:
        """测试执行模式显示智能确认."""
        tmp_path, files = sample_files

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            mock_confirm.return_value = True

            runner.invoke(
                cli, ["replace", "TODO:DONE", "--path", str(tmp_path), "--execute"]
            )

            # 应该调用智能确认
            assert mock_confirm.called

            # 检查确认参数
            call_args = mock_confirm.call_args[1]
            assert "3 个文件中替换 7 处文本" in call_args["operation"]
            assert call_args["dangerous"] is True
            assert len(call_args["files_affected"]) == 3
            assert len(call_args["preview_items"]) == 3

            # 检查预览内容格式
            preview = call_args["preview_items"][0]
            assert "TODO" in preview
            assert "DONE" in preview
            assert "→" in preview

    def test_skip_confirm_with_yes_flag(
        self, runner: CliRunner, sample_files: tuple[Path, list[Path]]
    ) -> None:
        """测试 --yes 参数跳过确认."""
        tmp_path, files = sample_files

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            result = runner.invoke(
                cli,
                ["replace", "TODO:DONE", "--path", str(tmp_path), "--execute", "--yes"],
            )

            # 不应该调用确认
            assert not mock_confirm.called
            assert result.exit_code == 0

            # 验证替换已执行
            for file in files:
                content = file.read_text()
                assert "DONE" in content
                assert "TODO" not in content

    def test_cancel_operation(
        self, runner: CliRunner, sample_files: tuple[Path, list[Path]]
    ) -> None:
        """测试取消操作."""
        tmp_path, files = sample_files

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            mock_confirm.return_value = False

            result = runner.invoke(
                cli, ["replace", "TODO:DONE", "--path", str(tmp_path), "--execute"]
            )

            assert mock_confirm.called
            assert "操作已取消" in result.output

            # 验证文件未被修改
            for file in files:
                content = file.read_text()
                assert "TODO" in content
                assert "DONE" not in content

    def test_dry_run_no_confirm(
        self, runner: CliRunner, sample_files: tuple[Path, list[Path]]
    ) -> None:
        """测试预览模式不需要确认."""
        tmp_path, files = sample_files

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            result = runner.invoke(
                cli, ["replace", "TODO:DONE", "--path", str(tmp_path)]
            )

            # 预览模式不应该调用确认
            assert not mock_confirm.called
            assert "预览模式完成" in result.output

    def test_smart_confirm_preview_items_limit(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """测试预览项目数量限制."""
        # 创建多个文件
        for i in range(10):
            file = tmp_path / f"file{i}.txt"
            file.write_text(f"TODO task {i}")

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            mock_confirm.return_value = True

            runner.invoke(
                cli, ["replace", "TODO:DONE", "--path", str(tmp_path), "--execute"]
            )

            # 检查预览项目数量
            call_args = mock_confirm.call_args[1]
            assert len(call_args["preview_items"]) == 5  # 最多显示5个
            assert len(call_args["files_affected"]) == 10  # 但影响所有文件

    def test_high_risk_flag_always_true(
        self, runner: CliRunner, sample_files: tuple[Path, list[Path]]
    ) -> None:
        """测试文本替换始终被标记为高风险."""
        tmp_path, files = sample_files

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            mock_confirm.return_value = True

            # 即使只有一个文件
            runner.invoke(
                cli, ["replace", "TODO:DONE", "--file", str(files[0]), "--execute"]
            )

            # 仍然标记为危险操作
            call_args = mock_confirm.call_args[1]
            assert call_args["dangerous"] is True

    def test_empty_replacement_handling(
        self, runner: CliRunner, sample_files: tuple[Path, list[Path]]
    ) -> None:
        """测试空替换（删除文本）的处理."""
        tmp_path, files = sample_files

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            mock_confirm.return_value = True

            runner.invoke(
                cli,
                ["replace", "TODO:", "--path", str(tmp_path), "--execute"],  # 替换为空
            )

            # 检查预览显示
            call_args = mock_confirm.call_args[1]
            preview = call_args["preview_items"][0]
            assert "'TODO' → ''" in preview  # 明确显示替换为空

    def test_integration_with_progress(self, runner: CliRunner, tmp_path: Path) -> None:
        """测试与进度显示的集成."""
        # 创建超过阈值的文件数量（>20）
        for i in range(25):
            file = tmp_path / f"doc{i}.txt"
            file.write_text(f"TODO task {i}")

        with patch("simple_tools.core.text_replace.smart_confirm_sync") as mock_confirm:
            mock_confirm.return_value = True

            runner.invoke(
                cli, ["replace", "TODO:DONE", "--path", str(tmp_path), "--execute"]
            )

            # 确认被调用
            assert mock_confirm.called

            # 检查操作描述
            call_args = mock_confirm.call_args[1]
            assert "25 个文件" in call_args["operation"]
