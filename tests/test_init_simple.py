"""测试 __init__.py 模块 - 简化版"""

import os
import sys
from typing import Any


def test_init_with_format_json(monkeypatch: Any) -> None:
    """测试带 --format json 参数的初始化"""
    # 备份原始 argv
    original_argv = sys.argv.copy()

    try:
        # 设置 argv
        sys.argv = ["test", "--format", "json"]

        # 重新导入模块
        import importlib

        import simple_tools

        importlib.reload(simple_tools)

        # 验证版本号
        assert simple_tools.__version__ == "0.1.0"

    finally:
        # 恢复 argv
        sys.argv = original_argv


def test_init_with_format_csv(monkeypatch: Any) -> None:
    """测试带 --format csv 参数的初始化"""
    original_argv = sys.argv.copy()

    try:
        sys.argv = ["test", "--format", "csv"]

        import importlib

        import simple_tools

        importlib.reload(simple_tools)

        assert simple_tools.__version__ == "0.1.0"

    finally:
        sys.argv = original_argv


def test_init_with_env_variable(monkeypatch: Any) -> None:
    """测试环境变量控制的初始化"""
    # 设置环境变量
    monkeypatch.setenv("LOGFIRE_CONSOLE", "false")

    # 清理 argv
    original_argv = sys.argv.copy()
    sys.argv = ["test"]

    try:
        import importlib

        import simple_tools

        importlib.reload(simple_tools)

        assert simple_tools.__version__ == "0.1.0"

    finally:
        sys.argv = original_argv
        monkeypatch.delenv("LOGFIRE_CONSOLE", raising=False)


def test_init_normal_mode() -> None:
    """测试正常模式初始化"""
    # 清理环境
    original_argv = sys.argv.copy()
    sys.argv = ["test"]

    if "LOGFIRE_CONSOLE" in os.environ:
        del os.environ["LOGFIRE_CONSOLE"]

    try:
        import importlib

        import simple_tools

        importlib.reload(simple_tools)

        assert simple_tools.__version__ == "0.1.0"

    finally:
        sys.argv = original_argv
