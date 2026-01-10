"""
Tests for backtest engine module.
"""

import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backtest.backtest_engine import (
    run_backtest,
    run_backtest_multiple_symbols,
    run_backtest_all_symbols
)


class TestBacktestEngine(unittest.TestCase):
    """Test cases for backtest engine functionality."""
    
    @patch('src.backtest.backtest_engine.load_bars_for_backtest')
    @patch('src.backtest.backtest_engine.Backtest')
    def test_run_backtest_basic(self, mock_backtest_class, mock_load_bars):
        """Test basic backtest execution."""
        # Mock data loading
        mock_df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100.5, 101.5, 102.5],
            'Volume': [1000, 1100, 1200]
        })
        mock_load_bars.return_value = {'AAPL': mock_df}
        
        # Mock backtest instance
        mock_stats = MagicMock()
        mock_stats.__getitem__ = lambda self, key: 5.0 if key == 'Return [%]' else 1.5
        mock_stats._trades = pd.DataFrame()
        mock_stats._equity_curve = pd.DataFrame()
        
        mock_bt_instance = MagicMock()
        mock_bt_instance.run.return_value = mock_stats
        mock_backtest_class.return_value = mock_bt_instance
        
        # Test backtest
        result = run_backtest(
            strategy_class=MagicMock(),
            symbol='AAPL',
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        
        self.assertIn('stats', result)
        self.assertEqual(result['symbol'], 'AAPL')
        self.assertIn('strategy_name', result)
    
    @patch('src.backtest.backtest_engine.load_bars_for_backtest')
    def test_run_backtest_no_data(self, mock_load_bars):
        """Test backtest with no data."""
        mock_load_bars.return_value = {'AAPL': pd.DataFrame()}
        
        result = run_backtest(
            strategy_class=MagicMock(),
            symbol='AAPL',
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        
        self.assertIsNone(result['stats'])
    
    @patch('src.backtest.backtest_engine.run_backtest')
    def test_run_backtest_multiple_symbols(self, mock_run_backtest):
        """Test running backtests for multiple symbols."""
        # Mock individual backtest results
        mock_result = {
            'stats': MagicMock(),
            'symbol': 'AAPL',
            'strategy_name': 'TestStrategy'
        }
        mock_run_backtest.return_value = mock_result
        
        result = run_backtest_multiple_symbols(
            strategy_class=MagicMock(),
            symbols=['AAPL', 'MSFT'],
            start_date='2025-01-01',
            end_date='2025-01-31'
        )
        
        self.assertEqual(len(result), 2)
        self.assertIn('AAPL', result)
        self.assertIn('MSFT', result)
        self.assertEqual(mock_run_backtest.call_count, 2)
    
    @patch('src.backtest.backtest_engine.get_available_symbols')
    @patch('src.backtest.backtest_engine.run_backtest_multiple_symbols')
    def test_run_backtest_all_symbols(self, mock_run_multiple, mock_get_symbols):
        """Test running backtests for all available symbols."""
        mock_get_symbols.return_value = ['AAPL', 'MSFT', 'GOOGL']
        mock_run_multiple.return_value = {
            'AAPL': {'stats': MagicMock()},
            'MSFT': {'stats': MagicMock()},
            'GOOGL': {'stats': MagicMock()}
        }
        
        result = run_backtest_all_symbols(
            strategy_class=MagicMock(),
            start_date='2025-01-01',
            end_date='2025-01-31',
            max_symbols=2
        )
        
        self.assertEqual(len(result), 2)
        mock_run_multiple.assert_called_once()


if __name__ == '__main__':
    unittest.main()

