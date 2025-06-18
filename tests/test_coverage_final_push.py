"""针对性测试以达到 85% 覆盖率"""

from pathlib import Path

from simple_tools.core.file_tool import _scan_directory_with_progress
from simple_tools.utils.config_loader import ConfigLoader


def test_config_loader_additional() -> None:
    """测试配置加载器的额外功能"""
    from simple_tools.utils.config_loader import find_config_file

    # 测试查找配置文件（不存在的情况）
    config_path = find_config_file("/nonexistent/path")
    assert config_path is None

    # 测试加载不存在的配置文件
    loader = ConfigLoader()
    config = loader.load_config("/nonexistent/config.yml")
    assert config is not None  # 应该返回默认配置
    assert config.verbose is False  # 检查默认值


def test_scan_directory_edge_cases(tmp_path: Path) -> None:
    """测试目录扫描的边界情况"""
    # 创建一些测试文件和被排除的目录
    excluded_dir = tmp_path / ".venv"
    excluded_dir.mkdir()
    excluded_file = excluded_dir / "test.py"
    excluded_file.write_text("test")

    # 创建正常文件
    normal_file = tmp_path / "normal.txt"
    normal_file.write_text("normal")

    # 创建隐藏文件
    hidden_file = tmp_path / ".hidden"
    hidden_file.write_text("hidden")

    # 扫描目录（不显示隐藏文件）
    items = _scan_directory_with_progress(str(tmp_path), show_hidden=False)

    # 应该只包含 normal.txt
    assert len(items) == 1
    assert items[0]["name"] == "normal.txt"

    # 扫描目录（显示隐藏文件）
    items = _scan_directory_with_progress(str(tmp_path), show_hidden=True)

    # 应该包含 normal.txt 和 .hidden，但不包含 .venv
    names = [item["name"] for item in items]
    assert "normal.txt" in names
    assert ".hidden" in names
    assert ".venv" not in names  # 被排除了


def test_init_module_coverage() -> None:
    """测试 __init__ 模块的额外覆盖"""
    import subprocess

    # 测试带 --format plain 参数（不应该禁用日志）
    result = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            "-c",
            "import sys; sys.argv = ['test', '--format', 'plain']; import simple_tools",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # 测试只有 --format 没有值的情况
    result = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            "-c",
            "import sys; sys.argv = ['test', '--format']; import simple_tools",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_file_organizer_skipped_status(tmp_path: Path) -> None:
    """测试文件整理器的跳过状态"""
    from simple_tools.core.file_organizer import FileOrganizerTool, OrganizeConfig

    # 创建一个文件
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    # 创建目标目录和同名文件（模拟已存在的情况）
    target_dir = tmp_path / "文档"
    target_dir.mkdir()
    existing_file = target_dir / "test.txt"
    existing_file.write_text("existing")

    # 创建配置
    config = OrganizeConfig(path=str(tmp_path), mode="type", dry_run=True)

    organizer = FileOrganizerTool(config)
    items = organizer.create_organize_plan()

    # 应该有一个被跳过的项
    skipped_items = [item for item in items if item.status == "skipped"]
    assert len(skipped_items) > 0


def test_duplicate_finder_edge_case(tmp_path: Path) -> None:
    """测试重复文件查找器的边界情况"""
    from simple_tools.core.duplicate_finder import DuplicateConfig, DuplicateFinder

    # 创建配置（非递归模式）
    config = DuplicateConfig(path=str(tmp_path), recursive=False)

    finder = DuplicateFinder(config)

    # 空目录应该返回空列表
    result = finder.find_duplicates()
    assert result == []
