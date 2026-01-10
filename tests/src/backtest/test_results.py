"""
Tests for results module.
"""

import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backtest.results import (
    BacktestResult,
    ResultsDatabase,
    ResultsComparator
)


class TestBacktestResult(unittest.TestCase):
    """Test cases for BacktestResult class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
    
    def test_backtest_result_init(self):
        """Test BacktestResult initialization."""
        mock_stats = MagicMock()
        mock_stats.get.return_value = 10.5
        
        result = BacktestResult(
            symbol='AAPL',
            strategy_name='TestStrategy',
            stats=mock_stats,
            parameters={'short_window': 10}
        )
        
        self.assertEqual(result.symbol, 'AAPL')
        self.assertEqual(result.strategy_name, 'TestStrategy')
        self.assertIsNotNone(result.timestamp)
    
    def test_backtest_result_to_dict(self):
        """Test converting BacktestResult to dictionary."""
        mock_stats = MagicMock()
        mock_stats.get.side_effect = lambda key, default: {
            'Return [%]': 10.5,
            'Sharpe Ratio': 1.5,
            '# Trades': 50
        }.get(key, default)
        
        result = BacktestResult(
            symbol='AAPL',
            strategy_name='TestStrategy',
            stats=mock_stats,
            parameters={'short_window': 10},
            trades=pd.DataFrame({'price': [100, 101]}),
            equity=pd.DataFrame({'equity': [10000, 10100]})
        )
        
        result_dict = result.to_dict()
        
        self.assertIn('symbol', result_dict)
        self.assertIn('metrics', result_dict)
        self.assertEqual(result_dict['symbol'], 'AAPL')
        self.assertEqual(result_dict['num_trades'], 2)
    
    def test_backtest_result_get_summary(self):
        """Test getting summary from BacktestResult."""
        mock_stats = pd.Series({
            'Return [%]': 10.5,
            'Sharpe Ratio': 1.5,
            '# Trades': 50
        })
        
        result = BacktestResult(
            symbol='AAPL',
            strategy_name='TestStrategy',
            stats=mock_stats,
            parameters={'short_window': 10}
        )
        
        summary = result.get_summary()
        self.assertIsInstance(summary, pd.Series)


class TestResultsDatabase(unittest.TestCase):
    """Test cases for ResultsDatabase class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
    
    def test_save_result(self):
        """Test saving a result."""
        with patch('src.backtest.results.project_root', Path(self.temp_dir)):
            db = ResultsDatabase()
            
            mock_stats = MagicMock()
            result = BacktestResult(
                symbol='AAPL',
                strategy_name='TestStrategy',
                stats=mock_stats,
                parameters={'short_window': 10}
            )
            
            filepath = db.save_result(result)
            self.assertTrue(os.path.exists(filepath))
    
    def test_load_result(self):
        """Test loading a result."""
        with patch('src.backtest.results.project_root', Path(self.temp_dir)):
            db = ResultsDatabase()
            
            # Save a result first
            mock_stats = MagicMock()
            original_result = BacktestResult(
                symbol='AAPL',
                strategy_name='TestStrategy',
                stats=mock_stats,
                parameters={'short_window': 10}
            )
            
            filepath = db.save_result(original_result)
            
            # Load it back
            loaded_result = db.load_result(filepath)
            self.assertEqual(loaded_result.symbol, 'AAPL')
            self.assertEqual(loaded_result.strategy_name, 'TestStrategy')
    
    def test_list_results(self):
        """Test listing all results."""
        with patch('src.backtest.results.project_root', Path(self.temp_dir)):
            db = ResultsDatabase()
            
            # Save multiple results
            for symbol in ['AAPL', 'MSFT']:
                mock_stats = MagicMock()
                result = BacktestResult(
                    symbol=symbol,
                    strategy_name='TestStrategy',
                    stats=mock_stats,
                    parameters={'short_window': 10}
                )
                db.save_result(result)
            
            results = db.list_results('TestStrategy')
            self.assertGreaterEqual(len(results), 2)


class TestResultsComparator(unittest.TestCase):
    """Test cases for ResultsComparator class."""
    
    def test_compare_results(self):
        """Test comparing multiple results."""
        mock_stats1 = pd.Series({'Return [%]': 10.0, 'Sharpe Ratio': 1.5})
        mock_stats2 = pd.Series({'Return [%]': 15.0, 'Sharpe Ratio': 2.0})
        
        result1 = BacktestResult(
            symbol='AAPL',
            strategy_name='TestStrategy',
            stats=mock_stats1,
            parameters={'short_window': 10}
        )
        
        result2 = BacktestResult(
            symbol='MSFT',
            strategy_name='TestStrategy',
            stats=mock_stats2,
            parameters={'short_window': 20}
        )
        
        comparator = ResultsComparator()
        comparison = comparator.compare([result1, result2])
        
        self.assertIsInstance(comparison, pd.DataFrame)
        self.assertEqual(len(comparison), 2)
    
    def test_rank_by_metric(self):
        """Test ranking results by metric."""
        mock_stats1 = pd.Series({'Return [%]': 10.0})
        mock_stats2 = pd.Series({'Return [%]': 15.0})
        mock_stats3 = pd.Series({'Return [%]': 5.0})
        
        results = [
            BacktestResult('AAPL', 'TestStrategy', mock_stats1, {}),
            BacktestResult('MSFT', 'TestStrategy', mock_stats2, {}),
            BacktestResult('GOOGL', 'TestStrategy', mock_stats3, {})
        ]
        
        comparator = ResultsComparator()
        ranked = comparator.rank_by_metric(results, 'Return [%]')
        
        self.assertEqual(ranked[0].symbol, 'MSFT')  # Highest return
        self.assertEqual(ranked[-1].symbol, 'GOOGL')  # Lowest return


if __name__ == '__main__':
    unittest.main()

