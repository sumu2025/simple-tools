"""
文件整理工具测试
"""

import pytest
import tempfile
import os
from pathlib import Path
from simple_tools.core.file_organizer import (
    FileOrganizerTool,
    OrganizeConfig,
    FileCategory
)


class TestFileOrganizerTool:
    """文件整理工具测试类"""

    def test_classify_file(self):
        """测试文件分类功能"""
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

    def test_generate_target_path(self):
        """测试目标路径生成"""
        config = OrganizeConfig(path="/test", mode="type")
        organizer = FileOrganizerTool(config)

        # 模拟文件和类别
        file_path = Path("/test/photo.jpg")
        category = FileCategory(
            name="图片", icon="📷", folder_name="图片",
            extensions=[".jpg"]
        )

        target = organizer.generate_target_path(file_path, category)
        assert str(target) == "/test/图片/photo.jpg"

    def test_scan_files_basic(self, tmp_path):
        """测试基本文件扫描功能"""
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

    def test_organize_config_validation(self):
        """测试配置验证"""
        # 测试默认配置
        config = OrganizeConfig()
        assert config.path == "."
        assert config.mode == "type"
        assert config.dry_run is True

        # 测试自定义配置
        config = OrganizeConfig(
            path="/custom/path",
            mode="date",
            recursive=True,
            dry_run=False
        )
        assert config.path == "/custom/path"
        assert config.mode == "date"
        assert config.recursive is True
        assert config.dry_run is False
