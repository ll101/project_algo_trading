"""
Backtest Engine Module
Standardized backtesting execution with support for multiple symbols.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union, Type, Any
from datetime import datetime
import logging
import pandas as pd

from backtesting import Backtest

# Add project root to path for imports when running as script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.backtest.dataloader import (
    load_bars_for_backtest,
    load_multiple_symbols,
    get_available_symbols,
    validate_data_quality
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_backtest(
    strategy_class: Type,
    symbol: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    cash: float = 100000,
    commission: float = 0.002,
    exclusive_orders: bool = True,
    resample: Optional[str] = None,
    strategy_params: Optional[Dict[str, Any]] = None,
    plot: bool = False,
    plot_filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a single backtest for one symbol.
    
    Args:
        strategy_class: Strategy class to test
        symbol: Stock symbol
        start_date: Start date for backtest
        end_date: End date for backtest
        cash: Starting cash (default: 100000)
        commission: Commission rate (default: 0.002 = 0.2%)
        exclusive_orders: Whether to use exclusive orders (default: True)
        resample: Optional resampling rule (e.g., '1H', '1D')
        strategy_params: Optional dictionary of strategy parameters
        plot: Whether to generate plot (default: False)
        plot_filename: Optional filename for plot (default: auto-generated)
    
    Returns:
        Dictionary containing:
        - 'stats': Backtest statistics
        - 'trades': Trade history DataFrame
        - 'equity': Equity curve DataFrame
        - 'symbol': Symbol tested
        - 'strategy_name': Name of strategy class
        - 'parameters': Strategy parameters used
    """
    logger.info(f"Running backtest for {symbol} using {strategy_class.__name__}")
    
    # Load data
    try:
        df = load_bars_for_backtest(symbol, start_date, end_date, resample=resample)
        
        if df.empty:
            logger.warning(f"No data available for {symbol}")
            return {
                'stats': None,
                'trades': pd.DataFrame(),
                'equity': pd.DataFrame(),
                'symbol': symbol,
                'strategy_name': strategy_class.__name__,
                'parameters': strategy_params or {},
                'error': 'No data available'
            }
        
        # Validate data quality
        validation = validate_data_quality(df, symbol)
        if not validation['is_valid']:
            logger.warning(f"Data quality issues for {symbol}: {validation['warnings']}")
        
    except Exception as e:
        logger.error(f"Error loading data for {symbol}: {e}")
        return {
            'stats': None,
            'trades': pd.DataFrame(),
            'equity': pd.DataFrame(),
            'symbol': symbol,
            'strategy_name': strategy_class.__name__,
            'parameters': strategy_params or {},
            'error': str(e)
        }
    
    # Create backtest instance
    try:
        bt = Backtest(
            df,
            strategy_class,
            cash=cash,
            commission=commission,
            exclusive_orders=exclusive_orders
        )
        
        # Run backtest with optional parameters
        if strategy_params:
            stats = bt.run(**strategy_params)
        else:
            stats = bt.run()
        
        # Extract results
        trades = stats._trades if hasattr(stats, '_trades') else pd.DataFrame()
        equity = stats._equity_curve if hasattr(stats, '_equity_curve') else pd.DataFrame()
        
        # Generate plot if requested
        if plot:
            if plot_filename is None:
                plots_dir = project_root / 'src' / 'backtest' / 'reports'
                plots_dir.mkdir(parents=True, exist_ok=True)
                plot_filename = str(plots_dir / f"{symbol}_{strategy_class.__name__}_backtest.html")
            
            try:
                bt.plot(filename=plot_filename)
                logger.info(f"Plot saved to {plot_filename}")
            except Exception as e:
                logger.warning(f"Failed to generate plot: {e}")
        
        logger.info(f"Backtest completed for {symbol}: Return = {stats['Return [%]']:.2f}%")
        
        return {
            'stats': stats,
            'trades': trades,
            'equity': equity,
            'symbol': symbol,
            'strategy_name': strategy_class.__name__,
            'parameters': strategy_params or {},
            'plot_filename': plot_filename if plot else None
        }
        
    except Exception as e:
        logger.error(f"Error running backtest for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'stats': None,
            'trades': pd.DataFrame(),
            'equity': pd.DataFrame(),
            'symbol': symbol,
            'strategy_name': strategy_class.__name__,
            'parameters': strategy_params or {},
            'error': str(e)
        }


def run_backtest_multiple_symbols(
    strategy_class: Type,
    symbols: List[str],
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    cash: float = 100000,
    commission: float = 0.002,
    exclusive_orders: bool = True,
    resample: Optional[str] = None,
    strategy_params: Optional[Dict[str, Any]] = None,
    plot: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Run backtest for multiple symbols.
    
    Args:
        strategy_class: Strategy class to test
        symbols: List of stock symbols
        start_date: Start date for backtest
        end_date: End date for backtest
        cash: Starting cash per symbol (default: 100000)
        commission: Commission rate (default: 0.002)
        exclusive_orders: Whether to use exclusive orders (default: True)
        resample: Optional resampling rule
        strategy_params: Optional dictionary of strategy parameters
        plot: Whether to generate plots (default: False)
    
    Returns:
        Dictionary mapping symbol to backtest results
    """
    logger.info(f"Running backtests for {len(symbols)} symbols using {strategy_class.__name__}")
    
    results = {}
    
    for i, symbol in enumerate(symbols, 1):
        logger.info(f"[{i}/{len(symbols)}] Processing {symbol}...")
        
        result = run_backtest(
            strategy_class=strategy_class,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            cash=cash,
            commission=commission,
            exclusive_orders=exclusive_orders,
            resample=resample,
            strategy_params=strategy_params,
            plot=plot
        )
        
        results[symbol] = result
    
    # Summary
    successful = sum(1 for r in results.values() if r.get('stats') is not None)
    logger.info(f"Completed {successful}/{len(symbols)} backtests successfully")
    
    return results


def run_backtest_all_symbols(
    strategy_class: Type,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    cash: float = 100000,
    commission: float = 0.002,
    exclusive_orders: bool = True,
    resample: Optional[str] = None,
    strategy_params: Optional[Dict[str, Any]] = None,
    max_symbols: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Run backtest for all available symbols in database.
    
    Args:
        strategy_class: Strategy class to test
        start_date: Start date for backtest
        end_date: End date for backtest
        cash: Starting cash per symbol (default: 100000)
        commission: Commission rate (default: 0.002)
        exclusive_orders: Whether to use exclusive orders (default: True)
        resample: Optional resampling rule
        strategy_params: Optional dictionary of strategy parameters
        max_symbols: Optional limit on number of symbols to test
    
    Returns:
        Dictionary mapping symbol to backtest results
    """
    # Get all available symbols
    symbols = get_available_symbols()
    
    if max_symbols:
        symbols = symbols[:max_symbols]
        logger.info(f"Limiting to first {max_symbols} symbols")
    
    logger.info(f"Running backtests for all {len(symbols)} available symbols")
    
    return run_backtest_multiple_symbols(
        strategy_class=strategy_class,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        cash=cash,
        commission=commission,
        exclusive_orders=exclusive_orders,
        resample=resample,
        strategy_params=strategy_params,
        plot=False  # Don't plot for all symbols
    )


# Example usage
if __name__ == "__main__":
    from src.strategy.strategies import MovingAverageCrossOverStrategy
    
    # Example: Single symbol backtest
    result = run_backtest(
        strategy_class=MovingAverageCrossOverStrategy,
        symbol="AAPL",
        start_date="2025-07-01",
        end_date="2025-08-31",
        cash=100000,
        commission=0.002,
        strategy_params={'short_window': 5, 'long_window': 20, 'ma_type': 'ema'},
        plot=True
    )
    
    if result['stats']:
        print(f"\nBacktest Results for {result['symbol']}:")
        print(result['stats'])
