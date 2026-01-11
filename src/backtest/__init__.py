"""
Backtesting Module
Provides data loading and backtesting infrastructure for trading strategies.
"""

from src.backtest.dataloader import (
    load_bars_from_db,
    load_multiple_symbols,
    get_available_symbols,
    get_nasdaq100_symbols,
    get_symbol_data_range,
    validate_data_quality,
    load_bars_for_backtest,
)

from src.backtest.backtest_engine import (
    run_backtest,
    run_backtest_multiple_symbols,
    run_backtest_all_symbols,
    run_portfolio_backtest,
)

from src.backtest.optimizer import (
    grid_search,
    random_search,
    cross_validate_optimize,
    create_time_series_kfold
)

from src.backtest.results import (
    BacktestResult,
    ResultsDatabase,
    ResultsComparator,
    save_results_batch,
    load_experiment_results,
)

__all__ = [
    # Data loading
    'load_bars_from_db',
    'load_multiple_symbols',
    'get_available_symbols',
    'get_nasdaq100_symbols',
    'get_symbol_data_range',
    'validate_data_quality',
    'load_bars_for_backtest',
    # Backtesting
    'run_backtest',
    'run_backtest_multiple_symbols',
    'run_backtest_all_symbols',
    'run_portfolio_backtest',
    # Optimization
    'grid_search',
    'random_search',
    'cross_validate_optimize',
    'create_time_series_kfold',
    # Results
    'BacktestResult',
    'ResultsDatabase',
    'ResultsComparator',
    'save_results_batch',
    'load_experiment_results',
]

