#!/bin/bash
# run_tests.sh
# Run all tests for the project

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo "Running Tests"
echo "=========================================="
echo ""

# Change to project root
cd "${PROJECT_ROOT}"

# Run Python tests
echo "Running Python unit tests..."
echo "----------------------------------------"
python -m pytest tests/ -v --tb=short

echo ""
echo "Running Python tests with unittest..."
echo "----------------------------------------"
python -m unittest discover -s tests -p "test_*.py" -v

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="

