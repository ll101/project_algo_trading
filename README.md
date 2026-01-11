# Algorithmic Trading Backtesting System

A comprehensive Python framework for backtesting trading strategies with TimescaleDB data storage, strategy optimization, and portfolio-level analysis.

## Features

- **Multiple Trading Strategies**: Moving Average Crossover, MACD, Bollinger Bands
- **Backtesting Engine**: Run backtests on single or multiple symbols
- **Parameter Optimization**: Grid search and random search optimization
- **Portfolio Analysis**: Portfolio-level backtesting across multiple symbols
- **TimescaleDB Integration**: Efficient time-series data storage and retrieval
- **Results Management**: Save, load, and compare backtest results
- **Data Quality Validation**: Automatic data quality checks and gap detection

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- TimescaleDB (via Docker)
- Alpaca API credentials (for data ingestion)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd project_algo_trading

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Setup Docker and Database

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Setup TimescaleDB container
./scripts/setup_docker.sh
```

This will:
- Create and start a TimescaleDB Docker container
- Initialize the database schema
- Set up hypertables for time-series data

**Note**: The database runs on port `5433` (host) → `5432` (container).

### 3. Configure Environment Variables

Create a `.env` file in the project root (optional, defaults are used if not set):

```env
# TimescaleDB Configuration
TIMESCALEDB_HOST=localhost
TIMESCALEDB_PORT=5433
TIMESCALEDB_DB=trading_db
TIMESCALEDB_USER=postgres
TIMESCALEDB_PASSWORD=postgres

# Alpaca API Configuration (for data ingestion)
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### 4. Ingest Market Data

```python
from src.data import alpaca_ingestion

# Ingest data for specific symbols and date range
alpaca_ingestion.main(
    start_date="2025-01-01",
    end_date="2025-06-30",
    symbols=["AAPL", "MSFT", "GOOGL"]
)
```

## Usage Examples

### Single Symbol Backtest

```python
from src.backtest import run_backtest
from src.strategy import MovingAverageCrossOverStrategy

result = run_backtest(
    strategy_class=MovingAverageCrossOverStrategy,
    symbol="AAPL",
    start_date="2025-01-01",
    end_date="2025-06-30",
    cash=100000,
    commission=0.002,
    strategy_params={
        'short_window': 10,
        'long_window': 50,
        'ma_type': 'sma',
        'stop_loss_pct': 0.02
    },
    plot=True
)

print(result['stats'])
```

### Multiple Symbols Backtest

```python
from src.backtest import run_backtest_multiple_symbols
from src.strategy import MovingAverageCrossOverStrategy

results = run_backtest_multiple_symbols(
    strategy_class=MovingAverageCrossOverStrategy,
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    start_date="2025-01-01",
    end_date="2025-06-30",
    strategy_params={'short_window': 10, 'long_window': 50}
)

for symbol, result in results.items():
    print(f"{symbol}: {result['stats'].get('Return [%]', 0):.2f}%")
```

### Portfolio-Level Backtest

```python
from src.backtest import run_portfolio_backtest
from src.strategy import MovingAverageCrossOverStrategy

portfolio_result = run_portfolio_backtest(
    strategy_class=MovingAverageCrossOverStrategy,
    symbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
    start_date="2025-01-01",
    end_date="2025-06-30",
    cash_per_symbol=100000
)

print(portfolio_result['portfolio_summary'])
```

### Parameter Optimization

```python
from src.backtest import grid_search
from src.strategy import MovingAverageCrossOverStrategy

optimization_result = grid_search(
    strategy_class=MovingAverageCrossOverStrategy,
    symbol="AAPL",
    start_date="2025-01-01",
    end_date="2025-06-30",
    param_grid={
        'short_window': [5, 10, 20],
        'long_window': [50, 100, 200],
        'ma_type': ['sma', 'ema']
    },
    maximize='Return [%]',
    return_heatmap=True
)

print(f"Best parameters: {optimization_result['best_params']}")
print(f"Best return: {optimization_result['best_value']:.2f}%")
```

### Save and Compare Results

```python
from src.backtest import (
    run_backtest_multiple_symbols,
    save_results_batch,
    load_experiment_results,
    ResultsComparator
)
from src.strategy import MovingAverageCrossOverStrategy

# Run backtests
results = run_backtest_multiple_symbols(
    strategy_class=MovingAverageCrossOverStrategy,
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    start_date="2025-01-01",
    end_date="2025-06-30"
)

# Save results
save_results_batch(results, experiment_name='ma_crossover_test')

# Load and compare
loaded_results = load_experiment_results('ma_crossover_test')
comparator = ResultsComparator(loaded_results)

# Compare summary
comparison = comparator.compare_summary()
print(comparison)
```

## Available Strategies

- **MovingAverageCrossOverStrategy**: Fast/slow moving average crossover
- **MACDStrategy**: MACD line and signal line crossover
- **BollingerBandsStrategy**: Bollinger Bands mean reversion

All strategies inherit from `BaseStrategy` and support:
- Stop loss and take profit
- Configurable parameters
- Risk management

## Project Structure

```
project_algo_trading/
├── src/
│   ├── backtest/          # Backtesting engine and optimization
│   │   ├── backtest_engine.py
│   │   ├── optimizer.py
│   │   ├── results.py
│   │   └── dataloader.py
│   ├── strategy/           # Trading strategies
│   │   ├── base.py
│   │   ├── strategies.py
│   │   └── indicators.py
│   ├── data/               # Data ingestion and database
│   │   ├── db_connection.py
│   │   ├── db_schema.py
│   │   └── alpaca_ingestion.py
│   └── notebooks/          # Jupyter notebooks for analysis
├── docker/                 # Docker configuration
│   ├── docker-compose.yml
│   └── init.sql
├── scripts/                # Setup and utility scripts
│   ├── setup_docker.sh
│   ├── start_container.sh
│   └── stop_container.sh
└── tests/                  # Unit and integration tests
```

## Docker Management

```bash
# Start container
./scripts/start_container.sh

# Stop container
./scripts/stop_container.sh

# Check container status
./scripts/check_container.sh

# Re-initialize database
./scripts/init_database.sh
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/src/backtest/test_dataloader.py -v
```

## Data Sources

The system supports data ingestion from:
- **Alpaca API**: Historical and real-time market data
- **TimescaleDB**: Local time-series database for efficient queries

## Results Storage

Backtest results are stored in:
- `src/backtest/results/` - JSON files for experiment results
- `src/backtest/reports/` - Generated plots and visualizations

## Contributing

1. Create a new strategy by inheriting from `BaseStrategy`
2. Implement `init()` and `next()` methods
3. Add strategy to `src/strategy/strategies.py`
4. Test with the backtesting engine

## License

[Add your license here]

## Notes

- The database uses TimescaleDB hypertables for optimized time-series queries
- All strategies support configurable stop loss and take profit
- Results can be saved and compared across different experiments
- The system supports resampling data to different timeframes (e.g., '1H', '1D')
