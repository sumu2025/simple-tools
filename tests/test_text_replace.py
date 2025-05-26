"""
文本替换工具单元测试
"""

import pytest
from pathlib import Path
from simple_tools.core.text_replace import TextReplaceTool, ReplaceConfig


class TestTextReplaceTool:
    """文本替换工具测试类"""

    def test_replace_config_properties(self):
        """测试替换配置属性解析"""
        config = ReplaceConfig(pattern="hello:world")
        assert config.old_text == "hello"
        assert config.new_text == "world"

        # 测试只有old_text的情况
        config2 = ReplaceConfig(pattern="hello")
        assert config2.old_text == "hello"
        assert config2.new_text == ""

    def test_scan_files_single_file(self, tmp_path):
        """测试单文件扫描"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        config = ReplaceConfig(
            pattern="hello:hi",
            file=str(test_file)
        )

        tool = TextReplaceTool(config)
        files = tool.scan_files()

        assert len(files) == 1
        assert files[0] == test_file

    def test_scan_files_directory(self, tmp_path):
        """测试目录扫描"""
        # 创建测试文件
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / ".hidden").write_text("hidden")

        config = ReplaceConfig(
            pattern="old:new",
            path=str(tmp_path)
        )

        tool = TextReplaceTool(config)
        files = tool.scan_files()

        # 应该找到2个文件（不包括隐藏文件）
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "file1.txt" in file_names
        assert "file2.py" in file_names
        assert ".hidden" not in file_names

    def test_scan_files_with_extension_filter(self, tmp_path):
        """测试扩展名过滤"""
        # 创建不同扩展名的文件
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "file3.md").write_text("content3")

        config = ReplaceConfig(
            pattern="old:new",
            path=str(tmp_path),
            extensions=[".txt", ".md"]
        )

        tool = TextReplaceTool(config)
        files = tool.scan_files()

        # 应该只找到txt和md文件
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "file1.txt" in file_names
        assert "file3.md" in file_names
        assert "file2.py" not in file_names

    def test_process_file_preview(self, tmp_path):
        """测试文件预览处理"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_content = "hello world\nhello Python\ngoodbye world"
        test_file.write_text(test_content)

        config = ReplaceConfig(pattern="hello:hi")
        tool = TextReplaceTool(config)

        result = tool.process_file(test_file, execute=False)

        assert result.match_count == 2
        assert not result.replaced
        assert len(result.preview_lines) > 0
        assert result.error is None

    def test_process_file_execute(self, tmp_path):
        """测试文件执行替换"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        original_content = "hello world\nhello Python"
        test_file.write_text(original_content)

        config = ReplaceConfig(pattern="hello:hi")
        tool = TextReplaceTool(config)

        result = tool.process_file(test_file, execute=True)

        assert result.match_count == 2
        assert result.replaced
        assert result.error is None

        # 验证文件内容已更改
        new_content = test_file.read_text()
        assert "hi world" in new_content
        assert "hi Python" in new_content
        assert "hello" not in new_content

    def test_process_file_no_match(self, tmp_path):
        """测试没有匹配的文件"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("goodbye world")

        config = ReplaceConfig(pattern="hello:hi")
        tool = TextReplaceTool(config)

        result = tool.process_file(test_file, execute=False)

        assert result.match_count == 0
        assert not result.replaced
        assert len(result.preview_lines) == 0
        assert result.error is None

    def test_process_file_encoding_error(self, tmp_path):
        """测试编码错误处理"""
        # 创建二进制文件
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b'\x80\x81\x82\x83')

        config = ReplaceConfig(pattern="hello:hi")
        tool = TextReplaceTool(config)

        result = tool.process_file(test_file, execute=False)

        assert result.match_count == 0
        assert result.error is not None
        assert "编码错误" in result.error

    def test_nonexistent_file_handling(self):
        """测试不存在文件的处理"""
        config = ReplaceConfig(
            pattern="hello:hi",
            file="/nonexistent/file.txt"
        )

        tool = TextReplaceTool(config)
        files = tool.scan_files()

        # 不存在的文件应该被忽略
        assert len(files) == 0

    def test_empty_directory_handling(self, tmp_path):
        """测试空目录处理"""
        config = ReplaceConfig(
            pattern="hello:hi",
            path=str(tmp_path)
        )

        tool = TextReplaceTool(config)
        files = tool.scan_files()

        assert len(files) == 0
