#!/bin/bash
cd /Users/peacock/Projects/simple-tools
poetry run pytest tests/test_coverage_boost.py::TestAdditionalCoverage::test_progress_tracker_usage -v
