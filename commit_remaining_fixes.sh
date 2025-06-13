#!/bin/bash
cd /Users/peacock/Projects/simple-tools
echo "提交剩余的类型注解修复..."
git add .
git commit -m "fix: 修复剩余的类型注解错误"
echo "提交完成! 检查git状态..."
git status
echo "现在运行pre-commit验证..."
echo "=========================================="
git commit --amend -m "fix: 修复剩余的类型注解错误" --no-edit
echo "=========================================="
echo "完成!"
