#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "快速运行测试并检查覆盖率..."
echo "================================="

# 运行测试并获取覆盖率
poetry run pytest --cov=src/simple_tools --cov-report=term -q 2>&1 | tail -25

echo -e "\n================================="
echo "检查是否达到 85% 目标..."

# 再次运行并检查是否通过85%要求
poetry run pytest --cov=src/simple_tools --cov-fail-under=85 -q > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 已达到 85% 覆盖率目标！"
else
    echo "❌ 尚未达到 85% 覆盖率目标"
fi
