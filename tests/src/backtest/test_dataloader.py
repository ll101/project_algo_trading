"""
Tests for dataloader module.
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

from src.backtest.dataloader import (
    load_bars_from_db,
    load_multiple_symbols,
    get_available_symbols,
    get_symbol_data_range,
    validate_data_quality,
    load_bars_for_backtest
)


class TestDataLoader(unittest.TestCase):
    """Test cases for dataloader functionality."""
    
    @patch('src.backtest.dataloader.get_db_connection')
    def test_load_bars_from_db(self, mock_get_conn):
        """Test loading bars from database."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('2025-01-01 10:00:00', 100.0, 101.0, 99.0, 100.5, 1000),
            ('2025-01-01 10:01:00', 100.5, 101.5, 100.0, 101.0, 1100)
        ]
        mock_cursor.description = [
            ('time',), ('open',), ('high',), ('low',), ('close',), ('volume',)
        ]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        # Test loading bars
        df = load_bars_from_db(
            symbol='AAPL',
            start_date='2025-01-01',
            end_date='2025-01-02'
        )
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn('Open', df.columns)
        self.assertIn('Close', df.columns)
    
    @patch('src.backtest.dataloader.load_bars_from_db')
    def test_load_multiple_symbols(self, mock_load_bars):
        """Test loading multiple symbols."""
        mock_df = pd.DataFrame({
            'Open': [100, 101],
            'High': [101, 102],
            'Low': [99, 100],
            'Close': [100.5, 101.5],
            'Volume': [1000, 1100]
        })
        mock_load_bars.return_value = mock_df
        
        result = load_multiple_symbols(
            symbols=['AAPL', 'MSFT'],
            start_date='2025-01-01',
            end_date='2025-01-02'
        )
        
        self.assertEqual(len(result), 2)
        self.assertIn('AAPL', result)
        self.assertIn('MSFT', result)
        self.assertEqual(mock_load_bars.call_count, 2)
    
    @patch('src.backtest.dataloader.get_db_connection')
    def test_get_available_symbols(self, mock_get_conn):
        """Test getting available symbols from database."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [('AAPL',), ('MSFT',), ('GOOGL',)]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        symbols = get_available_symbols()
        
        self.assertIsInstance(symbols, list)
        self.assertGreater(len(symbols), 0)
        self.assertIn('AAPL', symbols)
    
    @patch('src.backtest.dataloader.get_db_connection')
    def test_get_symbol_data_range(self, mock_get_conn):
        """Test getting data range for a symbol."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('2025-01-01', '2025-01-31')
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        start_date, end_date = get_symbol_data_range('AAPL')
        
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)
    
    def test_validate_data_quality(self):
        """Test data quality validation."""
        # Valid data
        valid_df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100.5, 101.5, 102.5],
            'Volume': [1000, 1100, 1200]
        })
        valid_df.index = pd.date_range('2025-01-01', periods=3, freq='1H')
        
        issues = validate_data_quality(valid_df)
        self.assertEqual(len(issues), 0)
        
        # Invalid data (missing values)
        invalid_df = pd.DataFrame({
            'Open': [100, None, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100.5, 101.5, 102.5],
            'Volume': [1000, 1100, 1200]
        })
        invalid_df.index = pd.date_range('2025-01-01', periods=3, freq='1H')
        
        issues = validate_data_quality(invalid_df)
        self.assertGreater(len(issues), 0)
    
    @patch('src.backtest.dataloader.load_bars_from_db')
    def test_load_bars_for_backtest(self, mock_load_bars):
        """Test loading bars for backtesting."""
        mock_df = pd.DataFrame({
            'Open': [100, 101],
            'High': [101, 102],
            'Low': [99, 100],
            'Close': [100.5, 101.5],
            'Volume': [1000, 1100]
        })
        mock_load_bars.return_value = mock_df
        
        result = load_bars_for_backtest(
            symbol='AAPL',
            start_date='2025-01-01',
            end_date='2025-01-02'
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('AAPL', result)
        self.assertIsInstance(result['AAPL'], pd.DataFrame)


if __name__ == '__main__':
    unittest.main()

