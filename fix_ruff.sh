#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "使用 ruff --fix 自动修复可修复的问题..."
poetry run ruff check . --fix

echo -e "\n再次检查剩余的问题..."
poetry run ruff check .
