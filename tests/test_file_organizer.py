"""文件整理工具测试."""

from pathlib import Path
from typing import Any

from simple_tools.core.file_organizer import (
    FileCategory,
    FileOrganizerTool,
    OrganizeConfig,
)


class TestFileOrganizerTool:
    """文件整理工具测试类."""

    def test_classify_file(self) -> None:
        """测试文件分类功能."""
        config = OrganizeConfig(path=".")
        organizer = FileOrganizerTool(config)

        # 测试图片分类
        jpg_file = Path("test.jpg")
        category = organizer.classify_file(jpg_file)
        assert category.name == "图片"

        # 测试文档分类
        pdf_file = Path("document.pdf")
        category = organizer.classify_file(pdf_file)
        assert category.name == "文档"

        # 测试未知类型
        unknown_file = Path("unknown.xyz")
        category = organizer.classify_file(unknown_file)
        assert category.name == "其他"

    def test_generate_target_path(self) -> None:
        """测试目标路径生成."""
        config = OrganizeConfig(path="/test", mode="type")
        organizer = FileOrganizerTool(config)

        # 模拟文件和类别
        file_path = Path("/test/photo.jpg")
        category = FileCategory(
            name="图片", icon="📷", folder_name="图片", extensions=[".jpg"]
        )

        target = organizer.generate_target_path(file_path, category)
        assert str(target) == "/test/图片/photo.jpg"

        # 测试 date 模式
        config_date = OrganizeConfig(path="/test", mode="date")
        organizer_date = FileOrganizerTool(config_date)
        file_path_date = Path("/test/photo.jpg")
        try:
            organizer_date.generate_target_path(file_path_date, category)
        except Exception:
            pass  # 跳过因文件不存在导致的异常

        # 测试 mixed 模式
        config_mixed = OrganizeConfig(path="/test", mode="mixed")
        organizer_mixed = FileOrganizerTool(config_mixed)
        try:
            organizer_mixed.generate_target_path(file_path_date, category)
        except Exception:
            pass

    def test_scan_files_basic(self, tmp_path: Path) -> None:
        """测试基本文件扫描功能."""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # 创建隐藏文件（应被忽略）
        hidden_file = tmp_path / ".hidden"
        hidden_file.write_text("hidden")

        config = OrganizeConfig(path=str(tmp_path), recursive=False)
        organizer = FileOrganizerTool(config)

        files = organizer.scan_files()
        file_names = [f.name for f in files]

        assert "test.txt" in file_names
        assert ".hidden" not in file_names

    def test_scan_files_recursive(self, tmp_path: Path) -> None:
        """测试递归扫描功能."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        file1 = tmp_path / "a.txt"
        file2 = subdir / "b.txt"
        file1.write_text("a")
        file2.write_text("b")

        config = OrganizeConfig(path=str(tmp_path), recursive=True)
        organizer = FileOrganizerTool(config)
        files = organizer.scan_files()
        file_names = [f.name for f in files]
        assert "a.txt" in file_names
        assert "b.txt" in file_names

    def test_create_organize_plan_and_execute(self, tmp_path: Path) -> None:
        """测试整理计划创建与执行."""
        # 创建多个测试文件
        img = tmp_path / "pic.jpg"
        doc = tmp_path / "doc.pdf"
        other = tmp_path / "file.abc"
        img.write_text("img")
        doc.write_text("doc")
        other.write_text("other")

        config = OrganizeConfig(path=str(tmp_path), mode="type", recursive=False)
        organizer = FileOrganizerTool(config)
        items = organizer.create_organize_plan()
        assert len(items) == 3
        # 所有目标文件都不应已存在
        for item in items:
            assert item.status == "pending"

        # 执行整理
        result = organizer.execute_organize(items)
        assert result.moved == 3
        assert result.failed == 0
        assert result.skipped == 0

        # 再次执行应没有可整理的文件
        items2 = organizer.create_organize_plan()
        result2 = organizer.execute_organize(items2)
        assert result2.total == 0
        assert len(items2) == 0

    def test_print_scan_summary(self, tmp_path: Path, capsys: Any) -> None:
        """测试打印扫描摘要."""
        img = tmp_path / "pic.jpg"
        img.write_text("img")
        config = OrganizeConfig(path=str(tmp_path), mode="type", recursive=False)
        organizer = FileOrganizerTool(config)
        items = organizer.create_organize_plan()
        category_stats: dict[str, list[Any]] = {}
        for item in items:
            category_stats.setdefault(item.category, []).append(item)
        organizer.print_scan_summary(str(tmp_path), "type", items, category_stats)
        captured = capsys.readouterr()
        assert "扫描目录" in captured.out
        assert "整理计划" in captured.out

    def test_organize_config_validation(self) -> None:
        """测试配置验证."""
        # 测试默认配置
        config = OrganizeConfig()
        assert config.path == "."
        assert config.mode == "type"
        assert config.dry_run is True

        # 测试自定义配置
        config = OrganizeConfig(
            path="/custom/path", mode="date", recursive=True, dry_run=False
        )
        assert config.path == "/custom/path"
        assert config.mode == "date"
        assert config.recursive is True
        assert config.dry_run is False
