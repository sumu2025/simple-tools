#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "1. 运行新增的 smart_interactive 测试..."
poetry run pytest tests/test_smart_interactive_extended.py -v --tb=short | head -30

echo -e "\n2. 检查 smart_interactive 覆盖率..."
poetry run pytest tests/test_smart_interactive*.py --cov=src/simple_tools/utils/smart_interactive --cov-report=term-missing -q | grep -A5 "smart_interactive"

echo -e "\n3. 运行所有测试检查总覆盖率..."
poetry run pytest --cov=src/simple_tools --cov-report=term -q | tail -15
