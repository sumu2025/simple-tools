"""测试文件整理工具的智能确认功能."""

from pathlib import Path

from click.testing import CliRunner

from simple_tools.core.file_organizer import organize_cmd


class TestFileOrganizerSmartConfirm:
    """测试文件整理工具的智能确认集成."""

    def test_organize_with_confirmation_yes(
        self, temp_dir: Path, cli_runner: CliRunner
    ) -> None:
        """测试用户确认执行的情况."""
        # 创建测试文件
        (temp_dir / "test1.txt").write_text("content1")
        (temp_dir / "test2.pdf").write_text("content2")
        (temp_dir / "image.jpg").write_text("image")

        # 创建模拟配置
        mock_ctx = {
            "config": type("Config", (), {"verbose": False, "organize": None})()
        }

        # 运行命令（在测试环境中会自动确认）
        result = cli_runner.invoke(
            organize_cmd,
            [str(temp_dir), "--execute"],
            obj=mock_ctx,
        )

        # 验证执行成功
        assert result.exit_code == 0
        # 智能交互系统在测试环境中会显示操作预览但自动确认
        assert "📋 操作:" in result.output or "操作:" in result.output
        assert "风险评估" in result.output
        assert "影响文件" in result.output
        assert "正在整理文件..." in result.output
        assert "成功移动:" in result.output

        # 验证文件被移动到正确的目录
        assert (temp_dir / "文档" / "test1.txt").exists()
        assert (temp_dir / "文档" / "test2.pdf").exists()
        assert (temp_dir / "图片" / "image.jpg").exists()

    def test_organize_shows_smart_confirmation(
        self, temp_dir: Path, cli_runner: CliRunner
    ) -> None:
        """测试智能确认显示正确的信息."""
        # 创建测试文件
        (temp_dir / "test1.txt").write_text("content1")
        (temp_dir / "test2.pdf").write_text("content2")

        # 创建模拟配置
        mock_ctx = {
            "config": type("Config", (), {"verbose": False, "organize": None})()
        }

        # 运行命令（在测试环境中会自动确认）
        result = cli_runner.invoke(
            organize_cmd,
            [str(temp_dir), "--execute"],
            obj=mock_ctx,
        )

        # 验证智能确认显示了预期的信息
        assert result.exit_code == 0
        assert "操作:" in result.output
        assert "整理 2 个文件" in result.output
        assert "风险评估" in result.output
        assert "安全操作" in result.output  # 文件数量少，风险低
        assert "影响文件 (2个)" in result.output
        assert "变更预览" in result.output
        assert "test1.txt → 文档/test1.txt" in result.output
        assert "test2.pdf → 文档/test2.pdf" in result.output

    def test_organize_with_yes_flag(
        self, temp_dir: Path, cli_runner: CliRunner
    ) -> None:
        """测试使用 --yes 参数跳过确认."""
        # 创建测试文件
        (temp_dir / "test1.txt").write_text("content1")
        (temp_dir / "test2.pdf").write_text("content2")

        # 创建模拟配置
        mock_ctx = {
            "config": type("Config", (), {"verbose": False, "organize": None})()
        }

        # 运行命令，使用 --yes 参数
        result = cli_runner.invoke(
            organize_cmd,
            [str(temp_dir), "--execute", "--yes"],
            obj=mock_ctx,
        )

        # 验证直接执行，没有确认提示
        assert result.exit_code == 0
        assert "确认执行?" not in result.output
        assert "正在整理文件..." in result.output
        assert "成功移动:" in result.output

        # 验证文件被移动
        assert (temp_dir / "文档" / "test1.txt").exists()
        assert (temp_dir / "文档" / "test2.pdf").exists()

    def test_organize_dry_run_no_confirmation(
        self, temp_dir: Path, cli_runner: CliRunner
    ) -> None:
        """测试预览模式不需要确认."""
        # 创建测试文件
        (temp_dir / "test1.txt").write_text("content1")

        # 创建模拟配置
        mock_ctx = {
            "config": type("Config", (), {"verbose": False, "organize": None})()
        }

        # 运行命令，默认是预览模式
        result = cli_runner.invoke(
            organize_cmd,
            [str(temp_dir)],
            obj=mock_ctx,
        )

        # 验证没有确认提示
        assert result.exit_code == 0
        assert "确认执行?" not in result.output
        assert "整理计划" in result.output
        assert "预览模式" in result.output

    def test_organize_shows_risk_assessment(
        self, temp_dir: Path, cli_runner: CliRunner
    ) -> None:
        """测试显示风险评估信息."""
        # 创建大量测试文件以触发高风险警告
        for i in range(60):
            (temp_dir / f"file{i}.txt").write_text(f"content{i}")

        # 创建模拟配置
        mock_ctx = {
            "config": type("Config", (), {"verbose": False, "organize": None})()
        }

        # 运行命令
        result = cli_runner.invoke(
            organize_cmd,
            [str(temp_dir), "--execute"],
            obj=mock_ctx,
            input="n\n",  # 取消操作
        )

        # 验证显示风险评估
        assert result.exit_code == 0
        assert "风险评估" in result.output or "风险等级" in result.output
        assert "60" in result.output  # 显示文件数量

    def test_organize_shows_preview_changes(
        self, temp_dir: Path, cli_runner: CliRunner
    ) -> None:
        """测试显示变更预览."""
        # 创建测试文件
        (temp_dir / "document.txt").write_text("content")
        (temp_dir / "photo.jpg").write_text("image")

        # 创建模拟配置
        mock_ctx = {
            "config": type("Config", (), {"verbose": False, "organize": None})()
        }

        # 运行命令
        result = cli_runner.invoke(
            organize_cmd,
            [str(temp_dir), "--execute"],
            obj=mock_ctx,
            input="n\n",
        )

        # 验证显示变更预览
        assert result.exit_code == 0
        assert "影响文件" in result.output or "document.txt" in result.output
        assert "→" in result.output  # 显示移动方向
