"""测试简单的工具函数以提升覆盖率"""

from pathlib import Path

import pytest

from simple_tools.core.duplicate_finder import format_size as dup_format_size
from simple_tools.core.file_tool import format_size, format_time
from simple_tools.utils.config_loader import merge_configs
from simple_tools.utils.formatter import FileListData, format_output


class TestSimpleUtilities:
    """测试简单的工具函数"""

    def test_format_size_edge_cases(self) -> None:
        """测试文件大小格式化的边界情况"""
        # 测试 0 字节
        assert format_size(0) == "0 B"
        assert dup_format_size(0) == "0 B"

        # 测试各种大小
        assert format_size(1) == "1.0 B"
        assert format_size(1023) == "1023.0 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"

        # 测试小数显示
        assert format_size(1536) == "1.5 KB"  # 1.5 * 1024
        assert format_size(1024 * 1024 * 1.5) == "1.5 MB"

    def test_format_time(self) -> None:
        """测试时间格式化"""
        # 使用固定的时间戳
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        # 注意：格式化后的时间会根据本地时区有所不同
        result = format_time(timestamp)
        assert "2021" in result or "2020" in result  # 根据时区可能是2020-12-31
        assert ":" in result  # 应该包含时间分隔符

    def test_merge_configs_edge_cases(self) -> None:
        """测试配置合并的边界情况"""
        from simple_tools.utils.config_loader import ToolConfig

        # 创建基础配置
        base_config = ToolConfig()
        assert base_config.verbose is False  # 默认值

        # 测试合并 - 修改 verbose
        cli_args = {"verbose": True}
        result = merge_configs(base_config, cli_args)
        assert result.verbose is True  # CLI 参数覆盖了默认值

        # 测试嵌套配置合并
        cli_args2: dict[str, bool] = {"verbose": False}
        result = merge_configs(base_config, cli_args2)
        assert result.verbose is False

        # 测试部分合并
        base_config = ToolConfig(verbose=True)
        cli_args3 = {"verbose": False}  # 只覆盖 verbose
        result = merge_configs(base_config, cli_args3)
        assert result.verbose is False  # 被覆盖

    def test_formatter_edge_cases(self) -> None:
        """测试格式化输出的边界情况"""
        # 测试空数据
        data = FileListData(path="/test", total=0, files=[])

        # JSON 格式
        json_output = format_output(data, "json")
        assert '"total": 0' in json_output
        assert '"files": []' in json_output

        # CSV 格式
        csv_output = format_output(data, "csv")
        assert "name,type,size" in csv_output

    def test_file_tool_error_cases(self, tmp_path: Path) -> None:
        """测试 file_tool 的错误处理"""
        from simple_tools.core.file_tool import list_files

        # 测试不存在的目录
        with pytest.raises(Exception):
            list_files("/nonexistent/path")

        # 测试文件而非目录
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with pytest.raises(Exception):
            list_files(str(test_file))
