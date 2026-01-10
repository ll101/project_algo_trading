"""
Tests for indicators module.
"""

import unittest
import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.indicators import (
    sma,
    ema,
    bollinger_bands,
    rsi,
    macd,
    atr,
    vwap
)


class TestIndicators(unittest.TestCase):
    """Test cases for indicator functions."""
    
    def setUp(self):
        """Set up test data."""
        np.random.seed(42)
        self.close_prices = np.array([100 + np.random.randn(100).cumsum()])
        self.close_prices = self.close_prices.flatten()
        self.high_prices = self.close_prices + np.abs(np.random.randn(100))
        self.low_prices = self.close_prices - np.abs(np.random.randn(100))
        self.volume = np.random.randint(1000, 10000, 100)
    
    def test_sma(self):
        """Test Simple Moving Average calculation."""
        period = 20
        result = sma(self.close_prices, period)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), len(self.close_prices))
        # First period-1 values should be NaN
        self.assertTrue(np.isnan(result[:period-1]).all())
        # Last value should be valid
        self.assertFalse(np.isnan(result[-1]))
    
    def test_sma_invalid_period(self):
        """Test SMA with invalid period."""
        with self.assertRaises(ValueError):
            sma(self.close_prices, -1)
        
        with self.assertRaises(ValueError):
            sma(self.close_prices, 0)
    
    def test_ema(self):
        """Test Exponential Moving Average calculation."""
        period = 20
        result = ema(self.close_prices, period)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), len(self.close_prices))
        # First period-1 values should be NaN
        self.assertTrue(np.isnan(result[:period-1]).all())
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        period = 20
        num_std = 2.0
        upper, middle, lower = bollinger_bands(self.close_prices, period, num_std)
        
        self.assertIsInstance(upper, np.ndarray)
        self.assertIsInstance(middle, np.ndarray)
        self.assertIsInstance(lower, np.ndarray)
        self.assertEqual(len(upper), len(self.close_prices))
        
        # Upper band should be above middle, lower should be below
        valid_idx = ~np.isnan(upper)
        if np.any(valid_idx):
            self.assertTrue(np.all(upper[valid_idx] >= middle[valid_idx]))
            self.assertTrue(np.all(lower[valid_idx] <= middle[valid_idx]))
    
    def test_rsi(self):
        """Test RSI calculation."""
        period = 14
        result = rsi(self.close_prices, period)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), len(self.close_prices))
        # RSI should be between 0 and 100
        valid_values = result[~np.isnan(result)]
        if len(valid_values) > 0:
            self.assertTrue(np.all(valid_values >= 0))
            self.assertTrue(np.all(valid_values <= 100))
    
    def test_macd(self):
        """Test MACD calculation."""
        fast_period = 12
        slow_period = 26
        signal_period = 9
        macd_line, signal_line, histogram = macd(
            self.close_prices, fast_period, slow_period, signal_period
        )
        
        self.assertIsInstance(macd_line, np.ndarray)
        self.assertIsInstance(signal_line, np.ndarray)
        self.assertIsInstance(histogram, np.ndarray)
        self.assertEqual(len(macd_line), len(self.close_prices))
    
    def test_atr(self):
        """Test ATR calculation."""
        period = 14
        result = atr(self.high_prices, self.low_prices, self.close_prices, period)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), len(self.close_prices))
        # ATR should be positive
        valid_values = result[~np.isnan(result)]
        if len(valid_values) > 0:
            self.assertTrue(np.all(valid_values >= 0))
    
    def test_vwap(self):
        """Test VWAP calculation."""
        # Create DataFrame-like structure
        high = self.high_prices
        low = self.low_prices
        close = self.close_prices
        volume = self.volume
        
        result = vwap(high, low, close, volume)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), len(close))
        # VWAP should be between low and high
        valid_idx = ~np.isnan(result)
        if np.any(valid_idx):
            self.assertTrue(np.all(result[valid_idx] >= low[valid_idx]))
            self.assertTrue(np.all(result[valid_idx] <= high[valid_idx]))


if __name__ == '__main__':
    unittest.main()

