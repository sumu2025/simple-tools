#!/bin/bash
cd /Users/peacock/Projects/simple-tools

# 运行performance_optimizer测试
echo "运行 performance_optimizer 测试..."
poetry run pytest tests/test_performance_optimizer.py -x --tb=short

# 如果成功，检查覆盖率
if [ $? -eq 0 ]; then
    echo -e "\n检查覆盖率..."
    poetry run pytest tests/test_performance_optimizer.py --cov=src/simple_tools/utils/performance_optimizer --cov-report=term-missing -q

    echo -e "\n检查总体覆盖率..."
    poetry run pytest --cov=src/simple_tools -q | grep -E "(performance_optimizer|TOTAL)"
fi
