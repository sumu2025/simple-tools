#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "运行失败的文本替换测试..."
poetry run pytest tests/test_text_replace.py tests/test_text_replace_cli.py tests/test_text_replace_smart_confirm.py -v --tb=short

echo -e "\n运行特定的失败测试..."
poetry run pytest tests/test_text_replace.py::TestTextReplaceTool::test_process_file_preview -xvs
