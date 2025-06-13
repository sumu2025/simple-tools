#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "运行 ruff 语法检查..."
poetry run ruff check .

# 如果语法检查通过，运行特定的测试
if [ $? -eq 0 ]; then
    echo -e "\n✅ 语法检查通过！"
    echo -e "\n运行 text_replace 测试..."
    poetry run pytest tests/test_text_replace.py -x --tb=short
else
    echo -e "\n❌ 仍有语法错误"
fi
