#!/bin/bash
echo "=== Running Ruff check ==="
cd /Users/peacock/Projects/simple-tools
poetry run ruff check .
ruff_exit=$?

echo -e "\n=== Running single test ==="
poetry run pytest tests/test_coverage_boost.py::TestAdditionalCoverage::test_progress_tracker_usage -v -s
test_exit=$?

echo -e "\n=== Summary ==="
echo "Ruff check exit code: $ruff_exit"
echo "Test exit code: $test_exit"

if [ $ruff_exit -eq 0 ] && [ $test_exit -eq 0 ]; then
    echo "All checks passed!"
    exit 0
else
    echo "Some checks failed!"
    exit 1
fi
