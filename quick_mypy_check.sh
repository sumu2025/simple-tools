#!/bin/bash
cd /Users/peacock/Projects/simple-tools
echo "=== 检查MyPy错误 ==="
poetry run mypy tests/test_errors.py
echo "退出码: $?"
