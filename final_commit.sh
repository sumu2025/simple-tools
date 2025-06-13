#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "尝试提交并检查 mypy 错误..."

# 直接提交当前修改
git add .
git commit -m "fix: 修复剩余的5个类型注解错误"

echo "提交完成!"
