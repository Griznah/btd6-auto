#!/usr/bin/env bash
# Helper script to run BTD6 automation tests correctly
# Ensures PYTHONPATH is set so relative imports work

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$PROJECT_ROOT"

# Usage info
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: ./run_tests.sh [pytest args]"
    echo "Runs the test suite with correct PYTHONPATH."
    echo "Examples:"
    echo "  ./run_tests.sh -v" 
    echo "  ./run_tests.sh tests/test_config.py -v"
    exit 0
fi

# Default: run all tests if no args
if [ $# -eq 0 ]; then
    pytest tests/ -v
else
    pytest "$@"
fi
