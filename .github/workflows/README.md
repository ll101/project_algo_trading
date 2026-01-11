# CI/CD Workflows

This directory contains GitHub Actions workflows for continuous integration.

## Workflows

### `test.yml` (Full)
- Runs tests with TimescaleDB service
- Includes database setup and health checks
- Suitable for integration tests that require database access
- More comprehensive but slower

### `test-simple.yml` (Simple)
- Runs tests without database service
- Faster execution
- Suitable for unit tests that use mocks
- Recommended for most use cases

## How It Works

1. **Triggers**: Runs on push to `main` and pull requests targeting `main`

2. **Changed Files Detection**: 
   - Detects which files changed in the commit/PR
   - Maps changed source files to corresponding test directories:
     - `src/data/` → `tests/src/data/`
     - `src/backtest/` → `tests/src/backtest/`
     - `src/strategy/` → `tests/src/strategy/`

3. **Test Execution**:
   - If specific modules changed: runs tests only for those modules
   - If test files changed: runs all tests
   - If no changes detected: runs all tests

## Usage

The workflows run automatically on push/PR. To run locally:

```bash
# Run all tests
python -m pytest tests/ -v
python -m unittest discover -s tests -p "test_*.py" -v

# Run specific module tests
python -m pytest tests/src/backtest/ -v
python -m unittest discover -s tests/src/backtest -p "test_*.py" -v
```

## Customization

To modify which tests run:
1. Edit the file mapping in the "Determine which tests to run" step
2. Adjust the `files` pattern in "Get changed files" step
3. Modify test execution commands in "Run tests" step

