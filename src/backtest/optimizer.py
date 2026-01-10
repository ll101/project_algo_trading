"""
Optimizer Module
Systematic parameter optimization for trading strategies.
Supports grid search, random search, and custom optimization methods.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union, Type, Any, Callable
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np
from itertools import product
from pprint import pprint
import csv
import json

from backtesting import Backtest
from backtesting.lib import plot_heatmaps

# Add project root to path for imports when running as script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.backtest.dataloader import load_bars_for_backtest, load_multiple_symbols
from src.backtest.backtest_engine import run_backtest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def grid_search(
    strategy_class: Type,
    symbol: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    param_grid: Dict[str, List[Any]],
    cash: float = 100000,
    commission: float = 0.002,
    exclusive_orders: bool = True,
    resample: Optional[str] = None,
    maximize: Union[str, Callable] = 'Return [%]',
    return_heatmap: bool = False
) -> Dict[str, Any]:
    """
    Perform grid search optimization over parameter space.
    
    Args:
        strategy_class: Strategy class to optimize
        symbol: Stock symbol
        start_date: Start date for backtest
        end_date: End date for backtest
        param_grid: Dictionary mapping parameter names to lists of values
                   Example: {'short_window': [5, 10, 20], 'long_window': [50, 100, 200]}
        cash: Starting cash (default: 100000)
        commission: Commission rate (default: 0.002)
        exclusive_orders: Whether to use exclusive orders (default: True)
        resample: Optional resampling rule
        maximize: Metric to maximize. Can be:
                 - String: Name of metric from backtest stats
                 - Callable: Function that takes stats dict and returns a value
        return_heatmap: Whether to return heatmap data (default: False)
    
    Returns:
        Dictionary containing:
        - 'best_params': Best parameter combination
        - 'best_stats': Statistics for best parameters
        - 'all_results': List of all parameter combinations and their stats
        - 'heatmap': Heatmap data (if return_heatmap=True)
    """
    logger.info(f"Starting grid search for {symbol} using {strategy_class.__name__}")
    logger.info(f"Parameter grid: {param_grid}")
    
    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    logger.info(f"Testing {len(combinations)} parameter combinations...")
    
    #Load data once
    try:
        df_dict = load_bars_for_backtest(symbol, start_date, end_date, resample=resample)
        df = df_dict[symbol]
        if df.empty:
            logger.error(f"No data available for {symbol}")
            return {'error': 'No data available'}
    except Exception as e:
        logger.error(f"Error loading data for {symbol}: {e}")
        return {'error': str(e)}
    
    # Create backtest instance
    bt = Backtest(df, strategy_class, cash=cash, commission=commission, exclusive_orders=exclusive_orders)
    
    # Run optimization
    try:
        stats, heatmap = bt.optimize(
            method='grid',
            maximize=maximize,
            return_heatmap=return_heatmap,
            **param_grid
        )
        
        # Extract best parameters
        best_params = {}
        for param_name in param_names:
            best_params[param_name] = stats._strategy.__dict__.get(param_name)
        
        logger.info(f"Optimization completed. Best parameters: {best_params}")
        logger.info(f"Best return: {stats['Return [%]']:.2f}%")
        
        result = {
            'best_params': best_params,
            'best_stats': stats,
            'symbol': symbol,
            'strategy_name': strategy_class.__name__,
            'param_grid': param_grid,
            'total_combinations': len(combinations)
        }
        
        if return_heatmap and heatmap is not None:
            result['heatmap'] = heatmap
        
        return result
        
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


def random_search(
    strategy_class: Type,
    symbol: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    param_distributions: Dict[str, List[Any]],
    n_iter: int = 50,
    cash: float = 100000,
    commission: float = 0.002,
    exclusive_orders: bool = True,
    resample: Optional[str] = None,
    maximize: Union[str, Callable] = 'Return [%]',
    random_state: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform random search optimization over parameter space.
    
    Args:
        strategy_class: Strategy class to optimize
        symbol: Stock symbol
        start_date: Start date for backtest
        end_date: End date for backtest
        param_distributions: Dictionary mapping parameter names to lists of values
        n_iter: Number of random combinations to test (default: 50)
        cash: Starting cash (default: 100000)
        commission: Commission rate (default: 0.002)
        exclusive_orders: Whether to use exclusive orders (default: True)
        resample: Optional resampling rule
        maximize: Metric to maximize
        random_state: Random seed for reproducibility
    
    Returns:
        Dictionary containing best parameters and statistics
    """
    logger.info(f"Starting random search for {symbol} using {strategy_class.__name__}")
    logger.info(f"Testing {n_iter} random parameter combinations...")
    
    # Set random seed if provided
    if random_state is not None:
        np.random.seed(random_state)
    
    # Load data once
    try:
        df_dict = load_bars_for_backtest(symbol, start_date, end_date, resample=resample)
        df = df_dict[symbol]
        if df.empty:
            logger.error(f"No data available for {symbol}")
            return {'error': 'No data available'}
    except Exception as e:
        logger.error(f"Error loading data for {symbol}: {e}")
        return {'error': str(e)}
    
    # Create backtest instance
    bt = Backtest(df, strategy_class, cash=cash, commission=commission, exclusive_orders=exclusive_orders)
    
    # Generate random parameter combinations
    param_names = list(param_distributions.keys())
    param_values = list(param_distributions.values())
    
    # Convert to ranges for random sampling
    param_ranges = {}
    for name, values in param_distributions.items():
        if isinstance(values[0], (int, float)):
            param_ranges[name] = range(min(values), max(values) + 1)
        else:
            param_ranges[name] = values
    
    try:
        stats = bt.optimize(
            method='random',
            maximize=maximize,
            n_trials=n_iter,
            random_state=random_state,
            **param_ranges
        )
        
        # Extract best parameters
        best_params = {}
        for param_name in param_names:
            best_params[param_name] = stats._strategy.__dict__.get(param_name)
        
        logger.info(f"Random search completed. Best parameters: {best_params}")
        logger.info(f"Best return: {stats['Return [%]']:.2f}%")
        
        return {
            'best_params': best_params,
            'best_stats': stats,
            'symbol': symbol,
            'strategy_name': strategy_class.__name__,
            'param_distributions': param_distributions,
            'n_iter': n_iter
        }
        
    except Exception as e:
        logger.error(f"Error during random search: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


# def cross_validation(
#     strategy_class: Type,
#     symbols: List[str],
#     start_date: Union[str, datetime],
#     end_date: Union[str, datetime],
#     param_grid: Dict[str, List[Any]],
#     time_k_folds: int = 1,
#     time_k_method: str = 'rolling',
#     cash: float = 100000,
#     commission: float = 0.002,
#     exclusive_orders: bool = True,
#     resample: Optional[str] = None,
#     maximize: Union[str, Callable] = 'Return [%]',
#     method: str = 'grid'
# ) -> Dict[str, Dict[str, Any]]:
#     """
#     Optimize strategy parameters across multiple symbols and time-series.
    
#     Args:
#         strategy_class: Strategy class to optimize
#         symbols: List of stock symbols
#         start_date: Start date for backtest
#         end_date: End date for backtest
#         param_grid: Parameter grid for optimization
#         cash: Starting cash (default: 100000)
#         commission: Commission rate (default: 0.002)
#         exclusive_orders: Whether to use exclusive orders (default: True)
#         resample: Optional resampling rule
#         maximize: Metric to maximize
#         method: Optimization method - 'grid' or 'random' (default: 'grid')
    
#     Returns:
#         Dictionary mapping symbol to optimization results
#     """
#     if time_k_folds < 1:
#         raise ValueError("time_k_folds must be an integer greater than or equal to 1")
    
#     if time_k_method not in ['rolling', 'expanding']:
#         raise ValueError("time_k_method must be 'rolling' or 'expanding'")
    
#     logger.info(f"Optimizing {strategy_class.__name__} for {len(symbols)} symbols.")
#     logger.info(f'Time series start date: {start_date}, end date: {end_date}')
#     logger.info(f'Method: {method}, Time-k folds: {time_k_folds}, Time-k method: {time_k_method}')
    

#     results = {}
  
#     time_fold_size = timedelta(days=int((end_date - start_date).days / time_k_folds))

#     print(f'days in each fold: {time_fold_size}')
    
#     for i, symbol in enumerate(symbols, 1):
#         logger.info(f"[{i}/{len(symbols)}] Optimizing {symbol}...")

#         for fold in range(time_k_folds):
#             if time_k_method == 'rolling':
#                 start_date_f = start_date + timedelta(days=fold*time_fold_size)
#                 end_date_f = start_date_f + timedelta(days=time_fold_size)
#             elif time_k_method == 'expanding':
#                 start_date_f = start_date
#                 end_date_f = start_date + timedelta(days=fold*time_fold_size)
#             else:
#                 raise ValueError(f"Invalid time_k_method: {time_k_method}")
        
#             if method == 'grid':
#                 result = grid_search(
#                     strategy_class=strategy_class,
#                     symbol=symbol,
#                     start_date=start_date_f,
#                     end_date=end_date_f,
#                     param_grid=param_grid,
#                     cash=cash,
#                     commission=commission,
#                     exclusive_orders=exclusive_orders,
#                     resample=resample,
#                     maximize=maximize
#                 )
#             elif method == 'random':
#                 result = random_search(
#                     strategy_class=strategy_class,
#                     symbol=symbol,
#                     start_date=start_date_f,
#                     end_date=end_date_f,
#                     param_distributions=param_grid,
#                     cash=cash,
#                     commission=commission,
#                     exclusive_orders=exclusive_orders,
#                     resample=resample,
#                     maximize=maximize
#                 )
#             else:
#                 logger.error(f"Unknown optimization method: {method}")
#                 result = {'error': f'Unknown method: {method}'}
            
#             fold_count = f'fold_{fold+1}'

#             results[symbol][fold_count] = result
    
#     # Summary
#     successful = sum(1 for r in results.values() if 'error' not in r)
#     logger.info(f"Optimization completed for {successful}/{len(symbols)} symbols")
#     experiment_time = datetime.now().strftime("%Y%m%d_%H%M%S")

#     # save experiment metadata to csv
#     experiment_metadata = {
#         'experiment_time': experiment_time,
#         'strategy_name': strategy_class.__name__,
#         'method': method,
#         'symbols': symbols,
#         'time_k_folds': time_k_folds,
#         'time_k_method': time_k_method,
#         'start_date': start_date,
#         'end_date': end_date
#     }
#     # check if results/cross_backtesting.csv exists, if not create the file and write the experiment metadata
#     if not os.path.exists('src/results/cross_backtesting.csv'):
#         with open('src/results/cross_backtesting.csv', 'w') as f:
#             writer = csv.writer(f)
#             writer.writerow(experiment_metadata.keys())
#             writer.writerow(experiment_metadata.values())
#     else:
#         with open('src/results/cross_backtesting.csv', 'a') as f:
#             writer = csv.writer(f)
#             writer.writerow(experiment_metadata.values())

#     # save results to json, organised by strategy folder
#     # check if the strategy folder exists under src/results/backtest, if not create the folder
#     if not os.path.exists(f'src/results/backtest/{strategy_class.__name__}'):
#         os.makedirs(f'src/results/backtest/{strategy_class.__name__}')
#     # then dump files to the strategy subfolder
#     with open(f'src/results/backtest/{strategy_class.__name__}/_{method}_{experiment_time}.json', 'w') as f:
#         json.dump(results, f)
    
#     return results


# def select_best_parameters(strategy_results_json_path: str, maximize: Union[str, Callable] = 'Return [%]'):
#     # check if the file exists
#     if not os.path.exists(strategy_results_json_path):
#         raise FileNotFoundError(f"File not found: {strategy_results_json_path}")
#     # then load the file
#     with open(strategy_results_json_path, 'r') as f:
#         results = json.load(f)
#     # select the best params based on the highest average of selected maximize metric in an experiment across all trials (each symbol and fold)
#     # each json file is an experiment with more than 1 symbol and fold
#     # each trial is the results from grid_search or random_search under the json[symbol][fold]
#     # after loading the json file, compute the highest average of the selected maximize metric across all trials
#     # return the best parameters and the highest average of the selected maximize metric

#     best_params = {}

#     average_maximize_metric = 0

#     num_of_trials = 0
#     for symbol, folds in results.items():
#         num_of_trials += len(folds)
#         for fold, trial in folds.items():
#             average_maximize_metric += trial['best_stats'][maximize]
#     average_maximize_metric /= num_of_trials
#     return best_params, average_maximize_metric

# Example usage
if __name__ == "__main__":
    from src.strategy.strategies import MovingAverageCrossOverStrategy
    
    # Example: Grid search optimization
    result = grid_search(
        strategy_class=MovingAverageCrossOverStrategy,
        symbol="AAPL",
        start_date="2025-07-01",
        end_date="2025-08-31",
        param_grid={
            'short_window': [5, 10, 20],
            'long_window': [50, 100, 200],
            'ma_type': ['sma', 'ema']
        },
        maximize='Return [%]',
        return_heatmap=True
    )
    
    pprint(result)

