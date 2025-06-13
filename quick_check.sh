#!/bin/bash
cd /Users/peacock/Projects/simple-tools

# 快速检查覆盖率
echo "检查当前覆盖率..."
poetry run pytest --cov=src/simple_tools --cov-report=term -q 2>&1 | tail -30
