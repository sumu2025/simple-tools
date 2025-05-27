"""pytest配置文件 - 提供测试环境的共享配置和fixtures."""

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, Callable

import logfire
import pytest


@pytest.fixture(scope="session", autouse=True)  # type: ignore[misc]
def configure_test_environment() -> Generator[None, None, None]:
    """自动配置测试环境."""
    os.environ["SIMPLE_TOOLS_TEST_MODE"] = "true"

    send_to_logfire = os.getenv("LOGFIRE_SEND_TO_LOGFIRE", "false").lower() == "true"
    service_name = os.getenv("LOGFIRE_SERVICE_NAME", "simple-tools-test")

    logfire.configure(
        service_name=service_name,
        send_to_logfire=send_to_logfire,
        console=False,
    )

    yield

    if "SIMPLE_TOOLS_TEST_MODE" in os.environ:
        del os.environ["SIMPLE_TOOLS_TEST_MODE"]


@pytest.fixture  # type: ignore[misc]
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录 fixture."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture  # type: ignore[misc]
def sample_text_files(temp_dir: Path) -> dict[str, Path]:
    """创建样本文本文件的 fixture."""
    files = {
        "config.txt": "server=localhost\nport=8080\ndebug=true\n",
        "readme.md": "# Project Title\nTODO: Add documentation\nTODO: Fix bugs\n",
        "script.py": "#!/usr/bin/env python3\nprint('Hello World')\n# TODO: optimize\n",
        "data.json": '{"name": "test", "value": "old_value"}\n',
        "notes.txt": "Meeting notes:\n- Discuss project\n- Review code\n",
    }
    created_files: dict[str, Path] = {}
    for filename, content in files.items():
        file_path = temp_dir / filename
        file_path.write_text(content, encoding="utf-8")
        created_files[filename] = file_path
    return created_files


@pytest.fixture  # type: ignore[misc]
def sample_binary_files(temp_dir: Path) -> dict[str, Path]:
    """创建样本二进制文件的 fixture."""
    files: dict[str, Path] = {}
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    files["binary.bin"] = binary_file
    empty_file = temp_dir / "empty.txt"
    empty_file.write_text("")
    files["empty.txt"] = empty_file
    return files


@pytest.fixture  # type: ignore[misc]
def mock_config() -> Any:
    """模拟配置对象的 fixture."""
    from simple_tools.config import get_config

    config = get_config()
    config.verbose = False
    if not hasattr(config, "test_mode"):
        config.test_mode = True
    return config


@pytest.fixture  # type: ignore[misc]
def duplicate_files(temp_dir: Path) -> dict[str, Path]:
    """创建包含重复文件的测试环境."""
    content = "This is duplicate content\nLine 2\nLine 3\n"
    files = {
        "file1.txt": content,
        "copy_of_file1.txt": content,
        "subdir/another_copy.txt": content,
        "different.txt": "This is different content\n",
        "unique.py": "print('unique content')\n",
    }
    created_files: dict[str, Path] = {}
    for filepath, file_content in files.items():
        full_path = temp_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(file_content, encoding="utf-8")
        created_files[filepath] = full_path
    return created_files


@pytest.fixture  # type: ignore[misc]
def rename_test_files(temp_dir: Path) -> list[Path]:
    """创建用于重命名测试的文件."""
    files = [
        "IMG_001.jpg",
        "IMG_002.jpg",
        "IMG_003.png",
        "document_draft.pdf",
        "report_old.docx",
    ]
    created_files: list[Path] = []
    for filename in files:
        file_path = temp_dir / filename
        file_path.write_text(f"Content of {filename}")
        created_files.append(file_path)
    return created_files


def pytest_configure(config: Any) -> None:
    """pytest启动时的配置."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """动态修改测试项目的配置."""
    for item in items:
        if not any(item.iter_markers()):
            if "integration" in item.name or "end_to_end" in item.name:
                item.add_marker(pytest.mark.integration)
            else:
                item.add_marker(pytest.mark.unit)
        if any(
            keyword in item.name.lower()
            for keyword in ["large", "big", "performance", "stress"]
        ):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)  # type: ignore[misc]
def reset_logfire_state() -> Generator[None, None, None]:
    """每个测试前重置logfire状态."""
    yield
    pass


@pytest.fixture  # type: ignore[misc]
def cli_runner() -> Any:
    """提供Click CLI测试运行器."""
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture  # type: ignore[misc]
def capture_output(capsys: Any) -> Callable[[], tuple[str, str]]:
    """捕获标准输出和错误输出的便利fixture."""

    def _capture() -> tuple[str, str]:
        captured = capsys.readouterr()
        return captured.out, captured.err

    return _capture
