#!/bin/bash
cd /Users/peacock/Projects/simple-tools
echo "=== 再次检查MyPy错误 ==="
poetry run mypy tests/test_errors.py --show-error-codes
echo "退出码: $?"

# 如果还有错误，尝试查看第320行的具体内容
echo ""
echo "=== 查看第320行内容 ==="
sed -n '315,325p' tests/test_errors.py | nl -v315
