#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "运行 ruff 检查..."
poetry run ruff check .

if [ $? -eq 0 ]; then
    echo -e "\n✅ 所有语法和风格检查都通过了！"

    echo -e "\n运行 text_replace 测试..."
    poetry run pytest tests/test_text_replace.py -v
else
    echo -e "\n❌ 仍有问题需要修复"
fi
