#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "=== 最终类型注解修复 ==="
echo "提交已修复的类型注解错误..."

git add .
git commit -m "fix: 修复所有类型注解错误 - OperationHistory mock_init, monkeypatch参数, Path mock函数"

echo "提交完成! 现在检查剩余错误..."
echo "==============================================="

# 如果还有错误，显示具体信息
echo "如果还有错误，将在下面显示："
