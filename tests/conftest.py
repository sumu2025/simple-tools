"""
pytest配置文件 - 提供测试环境的共享配置和fixtures
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
import logfire


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """
    自动配置测试环境
    - 禁用logfire的实际发送功能（避免测试数据污染）
    - 设置测试模式环境变量
    """
    # 设置自定义测试环境标识（不要用PYTEST_CURRENT_TEST，那是pytest内部使用的）
    os.environ["SIMPLE_TOOLS_TEST_MODE"] = "true"

    # 配置logfire为测试模式（只记录不发送）
    logfire.configure(
        service_name="simple-tools-test",
        send_to_logfire=False,  # 测试时不发送数据
        console=False  # 测试时不输出到控制台
    )

    yield

    # 清理自定义环境变量
    if "SIMPLE_TOOLS_TEST_MODE" in os.environ:
        del os.environ["SIMPLE_TOOLS_TEST_MODE"]


@pytest.fixture
def temp_dir():
    """
    创建临时目录fixture
    测试完成后自动清理
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path

    # 清理临时目录
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_text_files(temp_dir):
    """
    创建样本文本文件的fixture
    用于文本处理工具的测试
    """
    files = {
        "config.txt": "server=localhost\nport=8080\ndebug=true\n",
        "readme.md": "# Project Title\nTODO: Add documentation\nTODO: Fix bugs\n",
        "script.py": "#!/usr/bin/env python3\nprint('Hello World')\n# TODO: optimize\n",
        "data.json": '{"name": "test", "value": "old_value"}\n',
        "notes.txt": "Meeting notes:\n- Discuss project\n- Review code\n"
    }

    created_files = {}
    for filename, content in files.items():
        file_path = temp_dir / filename
        file_path.write_text(content, encoding='utf-8')
        created_files[filename] = file_path

    return created_files


@pytest.fixture
def sample_binary_files(temp_dir):
    """
    创建样本二进制文件的fixture
    用于测试二进制文件处理
    """
    files = {}

    # 创建一个小的二进制文件
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
    files["binary.bin"] = binary_file

    # 创建一个空文件
    empty_file = temp_dir / "empty.txt"
    empty_file.write_text("")
    files["empty.txt"] = empty_file

    return files


@pytest.fixture
def mock_config():
    """
    模拟配置对象的fixture
    """
    from simple_tools.config import get_config

    config = get_config()
    # 设置测试模式
    config.verbose = False
    # 如果config没有test_mode属性，则添加
    if not hasattr(config, 'test_mode'):
        config.test_mode = True

    return config


@pytest.fixture
def duplicate_files(temp_dir):
    """
    创建包含重复文件的测试环境
    用于测试重复文件查找功能
    """
    # 创建相同内容的文件
    content = "This is duplicate content\nLine 2\nLine 3\n"

    files = {
        "file1.txt": content,
        "copy_of_file1.txt": content,
        "subdir/another_copy.txt": content,
        "different.txt": "This is different content\n",
        "unique.py": "print('unique content')\n"
    }

    created_files = {}
    for filepath, file_content in files.items():
        full_path = temp_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(file_content, encoding='utf-8')
        created_files[filepath] = full_path

    return created_files


@pytest.fixture
def rename_test_files(temp_dir):
    """
    创建用于重命名测试的文件
    """
    files = [
        "IMG_001.jpg",
        "IMG_002.jpg",
        "IMG_003.png",
        "document_draft.pdf",
        "report_old.docx"
    ]

    created_files = []
    for filename in files:
        file_path = temp_dir / filename
        file_path.write_text(f"Content of {filename}")
        created_files.append(file_path)

    return created_files


# 设置pytest的一些全局配置
def pytest_configure(config):
    """pytest启动时的配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """
    动态修改测试项目的配置
    为没有标记的测试自动添加标记
    """
    for item in items:
        # 如果测试没有标记，根据测试名称自动添加标记
        if not any(item.iter_markers()):
            if "integration" in item.name or "end_to_end" in item.name:
                item.add_marker(pytest.mark.integration)
            else:
                item.add_marker(pytest.mark.unit)

        # 为可能耗时的测试添加slow标记
        if any(keyword in item.name.lower() for keyword in ["large", "big", "performance", "stress"]):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def reset_logfire_state():
    """
    每个测试前重置logfire状态
    确保测试之间不互相影响
    """
    # 测试开始前的设置
    yield
    # 测试结束后的清理（如果需要的话）
    pass


@pytest.fixture
def cli_runner():
    """
    提供Click CLI测试运行器
    用于测试CLI命令
    """
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def capture_output(capsys):
    """
    捕获标准输出和错误输出的便利fixture
    """
    def _capture():
        captured = capsys.readouterr()
        return captured.out, captured.err

    return _capture
