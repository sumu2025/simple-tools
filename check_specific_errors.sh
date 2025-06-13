#!/bin/bash
cd /Users/peacock/Projects/simple-tools
echo "运行mypy检查具体错误..."
poetry run mypy tests/test_smart_interactive_extended.py:112
poetry run mypy tests/test_performance_optimizer.py:258
poetry run mypy tests/test_performance_optimizer.py:263
poetry run mypy tests/test_errors.py:319
poetry run mypy tests/test_errors.py:490
echo "完成错误检查"
