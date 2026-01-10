"""
Tests for optimizer module.
"""

import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backtest.optimizer import (
    grid_search,
    random_search,
    save_result_to_file,
    load_result_from_file
)


class TestOptimizer(unittest.TestCase):
    """Test cases for optimizer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
    
    @patch('src.backtest.optimizer.load_bars_for_backtest')
    @patch('src.backtest.optimizer.Backtest')
    def test_grid_search_basic(self, mock_backtest_class, mock_load_bars):
        """Test basic grid search functionality."""
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
        mock_stats._strategy = MagicMock()
        mock_stats._strategy.__dict__ = {'short_window': 10, 'long_window': 50}
        mock_stats.__getitem__ = lambda self, key: 5.0 if key == 'Return [%]' else 1.5
        mock_stats.__contains__ = lambda self, key: True
        
        mock_heatmap = pd.DataFrame()
        mock_bt_instance = MagicMock()
        mock_bt_instance.optimize.return_value = (mock_stats, mock_heatmap)
        mock_backtest_class.return_value = mock_bt_instance
        
        # Test grid search
        result = grid_search(
            strategy_class=MagicMock(),
            symbol='AAPL',
            start_date='2025-01-01',
            end_date='2025-01-31',
            param_grid={'short_window': [5, 10], 'long_window': [50, 100]},
            maximize='Return [%]'
        )
        
        self.assertNotIn('error', result)
        self.assertIn('best_params', result)
        self.assertIn('best_stats', result)
        self.assertEqual(result['symbol'], 'AAPL')
    
    @patch('src.backtest.optimizer.load_bars_for_backtest')
    def test_grid_search_no_data(self, mock_load_bars):
        """Test grid search with no data."""
        mock_load_bars.return_value = {'AAPL': pd.DataFrame()}
        
        result = grid_search(
            strategy_class=MagicMock(),
            symbol='AAPL',
            start_date='2025-01-01',
            end_date='2025-01-31',
            param_grid={'short_window': [5, 10]}
        )
        
        self.assertIn('error', result)
    
    @patch('src.backtest.optimizer.load_bars_for_backtest')
    @patch('src.backtest.optimizer.Backtest')
    def test_random_search_basic(self, mock_backtest_class, mock_load_bars):
        """Test basic random search functionality."""
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
        mock_stats._strategy = MagicMock()
        mock_stats._strategy.__dict__ = {'short_window': 10, 'long_window': 50}
        mock_stats.__getitem__ = lambda self, key: 5.0 if key == 'Return [%]' else 1.5
        mock_stats.__contains__ = lambda self, key: True
        
        mock_bt_instance = MagicMock()
        mock_bt_instance.optimize.return_value = mock_stats
        mock_backtest_class.return_value = mock_bt_instance
        
        # Test random search
        result = random_search(
            strategy_class=MagicMock(),
            symbol='AAPL',
            start_date='2025-01-01',
            end_date='2025-01-31',
            param_distributions={'short_window': [5, 10, 20], 'long_window': [50, 100, 200]},
            n_iter=10
        )
        
        self.assertNotIn('error', result)
        self.assertIn('best_params', result)
        self.assertIn('best_stats', result)
    
    def test_save_result_to_file(self):
        """Test saving result to file."""
        # Create mock result
        mock_stats = pd.Series({
            'Return [%]': 10.5,
            'Sharpe Ratio': 1.5,
            '# Trades': 50
        })
        
        result = {
            'best_params': {'short_window': 10, 'long_window': 50},
            'best_stats': mock_stats,
            'symbol': 'AAPL',
            'strategy_name': 'TestStrategy',
            'param_grid': {'short_window': [5, 10]},
            'total_combinations': 4
        }
        
        with patch('src.backtest.optimizer.project_root', Path(self.temp_dir)):
            file_paths = save_result_to_file(
                result=result,
                strategy_name='TestStrategy',
                symbol='AAPL',
                method='grid',
                start_date='2025-01-01',
                end_date='2025-01-31'
            )
        
        self.assertIn('pkl_path', file_paths)
        self.assertIn('json_summary_path', file_paths)
        self.assertTrue(os.path.exists(file_paths['pkl_path']))
        self.assertTrue(os.path.exists(file_paths['json_summary_path']))
    
    def test_save_result_to_file_with_heatmap(self):
        """Test saving result with heatmap."""
        mock_stats = pd.Series({'Return [%]': 10.5})
        mock_heatmap = pd.DataFrame({'param1': [1, 2], 'param2': [3, 4]})
        
        result = {
            'best_params': {'short_window': 10},
            'best_stats': mock_stats,
            'symbol': 'AAPL',
            'strategy_name': 'TestStrategy',
            'heatmap': mock_heatmap
        }
        
        with patch('src.backtest.optimizer.project_root', Path(self.temp_dir)):
            file_paths = save_result_to_file(
                result=result,
                strategy_name='TestStrategy',
                symbol='AAPL',
                method='grid',
                start_date='2025-01-01',
                end_date='2025-01-31'
            )
        
        self.assertIsNotNone(file_paths['csv_heatmap_path'])
        self.assertTrue(os.path.exists(file_paths['csv_heatmap_path']))
    
    def test_load_result_from_file(self):
        """Test loading result from file."""
        import pickle
        
        # Create test result
        test_result = {
            'best_params': {'short_window': 10},
            'best_stats': pd.Series({'Return [%]': 10.5}),
            'symbol': 'AAPL'
        }
        
        # Save to temp file
        temp_file = os.path.join(self.temp_dir, 'test_result.pkl')
        with open(temp_file, 'wb') as f:
            pickle.dump(test_result, f)
        
        # Load and verify
        loaded_result = load_result_from_file(temp_file)
        self.assertEqual(loaded_result['symbol'], 'AAPL')
        self.assertIn('best_params', loaded_result)
        self.assertIsInstance(loaded_result['best_stats'], pd.Series)


if __name__ == '__main__':
    unittest.main()

