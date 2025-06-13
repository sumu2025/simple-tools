#!/bin/bash
cd /Users/peacock/Projects/simple-tools

echo "=== Checking Ruff ==="
poetry run ruff check src/simple_tools/core/text_replace.py | head -20

echo -e "\n=== Checking specific test ==="
poetry run pytest tests/test_coverage_boost.py::TestAdditionalCoverage::test_progress_tracker_usage -v --tb=short 2>&1 | grep -A5 -B5 -E "(test_progress_tracker_usage|Exit code|FAILED|PASSED|assert)"
