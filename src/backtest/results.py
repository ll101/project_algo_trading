"""
Results Management Module
Store, compare, and analyze backtest results.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from datetime import datetime
import logging
import json
import pandas as pd
import numpy as np

# Add project root to path for imports when running as script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestResult:
    """
    Container for a single backtest result.
    """
    
    def __init__(
        self,
        symbol: str,
        strategy_name: str,
        stats: Any,
        parameters: Dict[str, Any],
        trades: Optional[pd.DataFrame] = None,
        equity: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize backtest result.
        
        Args:
            symbol: Stock symbol
            strategy_name: Name of strategy class
            stats: Backtest statistics object
            parameters: Strategy parameters used
            trades: Trade history DataFrame
            equity: Equity curve DataFrame
            timestamp: Timestamp of backtest (default: now)
        """
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.stats = stats
        self.parameters = parameters
        self.trades = trades if trades is not None else pd.DataFrame()
        self.equity = equity if equity is not None else pd.DataFrame()
        self.timestamp = timestamp if timestamp else datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for storage.
        
        Returns:
            Dictionary representation of result
        """
        # Extract key metrics from stats
        metrics = {}
        if self.stats is not None:
            try:
                metrics = {
                    'return_pct': float(self.stats.get('Return [%]', 0)),
                    'buy_hold_return_pct': float(self.stats.get('Buy & Hold Return [%]', 0)),
                    'sharpe_ratio': float(self.stats.get('Sharpe Ratio', 0)),
                    'sortino_ratio': float(self.stats.get('Sortino Ratio', 0)),
                    'calmar_ratio': float(self.stats.get('Calmar Ratio', 0)),
                    'max_drawdown_pct': float(self.stats.get('Max. Drawdown [%]', 0)),
                    'volatility_pct': float(self.stats.get('Volatility (Ann.) [%]', 0)),
                    'total_trades': int(self.stats.get('# Trades', 0)),
                    'win_rate_pct': float(self.stats.get('Win Rate [%]', 0)),
                    'avg_trade_pct': float(self.stats.get('Avg. Trade [%]', 0)),
                    'profit_factor': float(self.stats.get('Profit Factor', 0)),
                }
            except Exception as e:
                logger.warning(f"Error extracting metrics: {e}")
                metrics = {}
        
        return {
            'symbol': self.symbol,
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'metrics': metrics,
            'timestamp': self.timestamp.isoformat(),
            'num_trades': len(self.trades),
            'num_equity_points': len(self.equity)
        }
    
    def get_summary(self) -> pd.Series:
        """
        Get summary statistics as pandas Series.
        
        Returns:
            Series with key metrics
        """
        if self.stats is None:
            return pd.Series()
        
        summary = pd.Series({
            'Symbol': self.symbol,
            'Strategy': self.strategy_name,
            'Return [%]': self.stats.get('Return [%]', 0),
            'Sharpe Ratio': self.stats.get('Sharpe Ratio', 0),
            'Max Drawdown [%]': self.stats.get('Max. Drawdown [%]', 0),
            'Total Trades': self.stats.get('# Trades', 0),
            'Win Rate [%]': self.stats.get('Win Rate [%]', 0),
            'Profit Factor': self.stats.get('Profit Factor', 0),
        })
        
        return summary


class ResultsDatabase:
    """
    Manage storage and retrieval of backtest results.
    """
    
    def __init__(self, results_dir: Optional[Path] = None):
        """
        Initialize results database.
        
        Args:
            results_dir: Directory to store results (default: project_root/src/results)
        """
        if results_dir is None:
            results_dir = project_root / 'src' / 'results'
        
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Results database initialized at {self.results_dir}")
    
    def save_result(self, result: BacktestResult, experiment_name: Optional[str] = None) -> str:
        """
        Save backtest result to file.
        
        Args:
            result: BacktestResult object
            experiment_name: Optional experiment name for organization
        
        Returns:
            Path to saved file
        """
        # Create filename
        timestamp_str = result.timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{result.symbol}_{result.strategy_name}_{timestamp_str}.json"
        
        if experiment_name:
            experiment_dir = self.results_dir / experiment_name
            experiment_dir.mkdir(parents=True, exist_ok=True)
            filepath = experiment_dir / filename
        else:
            filepath = self.results_dir / filename
        
        # Convert to dictionary
        result_dict = result.to_dict()
        
        # Save to JSON
        with open(filepath, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
        
        logger.info(f"Result saved to {filepath}")
        return str(filepath)
    
    def load_result(self, filepath: Union[str, Path]) -> BacktestResult:
        """
        Load backtest result from file.
        
        Args:
            filepath: Path to result file
        
        Returns:
            BacktestResult object
        """
        filepath = Path(filepath)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct result (stats object cannot be fully reconstructed)
        result = BacktestResult(
            symbol=data['symbol'],
            strategy_name=data['strategy_name'],
            stats=None,  # Stats object not stored, only metrics
            parameters=data['parameters'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )
        
        return result
    
    def list_results(self, experiment_name: Optional[str] = None) -> List[Path]:
        """
        List all result files.
        
        Args:
            experiment_name: Optional experiment name to filter
        
        Returns:
            List of result file paths
        """
        if experiment_name:
            search_dir = self.results_dir / experiment_name
        else:
            search_dir = self.results_dir
        
        if not search_dir.exists():
            return []
        
        result_files = list(search_dir.glob('*.json'))
        return sorted(result_files, reverse=True)  # Most recent first


class ResultsComparator:
    """
    Compare multiple backtest results.
    """
    
    def __init__(self, results: List[BacktestResult]):
        """
        Initialize comparator with list of results.
        
        Args:
            results: List of BacktestResult objects
        """
        self.results = results
    
    def compare_summary(self) -> pd.DataFrame:
        """
        Create comparison DataFrame of all results.
        
        Returns:
            DataFrame with one row per result, columns are metrics
        """
        summaries = []
        for result in self.results:
            summary = result.get_summary()
            if not summary.empty:
                summaries.append(summary)
        
        if not summaries:
            return pd.DataFrame()
        
        return pd.DataFrame(summaries)
    
    def rank_by_metric(self, metric: str, ascending: bool = False) -> pd.DataFrame:
        """
        Rank results by a specific metric.
        
        Args:
            metric: Metric name to rank by
            ascending: Whether to sort ascending (default: False)
        
        Returns:
            DataFrame sorted by metric
        """
        comparison = self.compare_summary()
        
        if metric not in comparison.columns:
            logger.warning(f"Metric '{metric}' not found in results")
            return comparison
        
        return comparison.sort_values(by=metric, ascending=ascending)
    
    def get_best_result(self, metric: str = 'Return [%]') -> Optional[BacktestResult]:
        """
        Get the best result by a specific metric.
        
        Args:
            metric: Metric to optimize (default: 'Return [%]')
        
        Returns:
            Best BacktestResult or None
        """
        comparison = self.compare_summary()
        
        if comparison.empty:
            return None
        
        if metric not in comparison.columns:
            logger.warning(f"Metric '{metric}' not found, using first result")
            return self.results[0]
        
        best_idx = comparison[metric].idxmax()
        best_symbol = comparison.loc[best_idx, 'Symbol']
        best_strategy = comparison.loc[best_idx, 'Strategy']
        
        # Find matching result
        for result in self.results:
            if result.symbol == best_symbol and result.strategy_name == best_strategy:
                return result
        
        return self.results[0]
    
    def compare_equity_curves(self) -> pd.DataFrame:
        """
        Compare equity curves across all results.
        
        Returns:
            DataFrame with equity curves as columns, indexed by time
        """
        equity_curves = {}
        
        for result in self.results:
            if not result.equity.empty:
                key = f"{result.symbol}_{result.strategy_name}"
                equity_curves[key] = result.equity['Equity']
        
        if not equity_curves:
            return pd.DataFrame()
        
        # Align by index (time)
        df = pd.DataFrame(equity_curves)
        return df


def save_results_batch(
    results: Dict[str, Dict[str, Any]],
    experiment_name: str,
    results_db: Optional[ResultsDatabase] = None
) -> List[str]:
    """
    Save a batch of backtest results.
    
    Args:
        results: Dictionary mapping symbol to result dict (from backtest_engine)
        experiment_name: Name for this experiment
        results_db: Optional ResultsDatabase instance
    
    Returns:
        List of saved file paths
    """
    if results_db is None:
        results_db = ResultsDatabase()
    
    saved_files = []
    
    for symbol, result_dict in results.items():
        if result_dict.get('stats') is None:
            continue
        
        result = BacktestResult(
            symbol=symbol,
            strategy_name=result_dict.get('strategy_name', 'Unknown'),
            stats=result_dict.get('stats'),
            parameters=result_dict.get('parameters', {}),
            trades=result_dict.get('trades', pd.DataFrame()),
            equity=result_dict.get('equity', pd.DataFrame())
        )
        
        filepath = results_db.save_result(result, experiment_name)
        saved_files.append(filepath)
    
    logger.info(f"Saved {len(saved_files)} results for experiment '{experiment_name}'")
    return saved_files


def load_experiment_results(
    experiment_name: str,
    results_db: Optional[ResultsDatabase] = None
) -> List[BacktestResult]:
    """
    Load all results from an experiment.
    
    Args:
        experiment_name: Name of experiment
        results_db: Optional ResultsDatabase instance
    
    Returns:
        List of BacktestResult objects
    """
    if results_db is None:
        results_db = ResultsDatabase()
    
    result_files = results_db.list_results(experiment_name)
    results = []
    
    for filepath in result_files:
        try:
            result = results_db.load_result(filepath)
            results.append(result)
        except Exception as e:
            logger.warning(f"Error loading result from {filepath}: {e}")
    
    logger.info(f"Loaded {len(results)} results from experiment '{experiment_name}'")
    return results


# Example usage
if __name__ == "__main__":
    # Example: Save and compare results
    from src.backtest.backtest_engine import run_backtest_multiple_symbols
    from src.strategy.strategies import MovingAverageCrossOverStrategy, VWAPReversionStrategy
    
    # Run backtests
    results = run_backtest_multiple_symbols(
        strategy_class=VWAPReversionStrategy,
        symbols=['AAPL'],
        start_date='2025-07-01',
        end_date='2025-08-31',
        resample='1H',
        strategy_params={'deviation_pct': 0.01, 'stop_loss_pct': 0.02}
    )
    
    # Save results
    saved_files = save_results_batch(results, experiment_name='vwap_reversion_test')
    
    # Load and compare
    loaded_results = load_experiment_results('vwap_reversion_test')
    comparator = ResultsComparator(loaded_results)
    
    # Compare summary
    comparison = comparator.compare_summary()
    print("\nComparison Summary:")
    print(comparison)
    
    # Rank by return
    ranked = comparator.rank_by_metric('Return [%]')
    print("\nRanked by Return:")
    print(ranked)

