"""
Tests for strategies module.
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.strategies import (
    MovingAverageCrossOverStrategy,
    BollingerBandsStrategy,
    MACDStrategy,
    VWAPReversionStrategy
)


class TestStrategies(unittest.TestCase):
    """Test cases for strategy implementations."""
    
    def setUp(self):
        """Set up test data."""
        # Create mock OHLCV data
        dates = pd.date_range('2025-01-01', periods=100, freq='1H')
        self.test_data = pd.DataFrame({
            'Open': 100 + np.random.randn(100).cumsum(),
            'High': 101 + np.random.randn(100).cumsum(),
            'Low': 99 + np.random.randn(100).cumsum(),
            'Close': 100.5 + np.random.randn(100).cumsum(),
            'Volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
    
    def test_moving_average_crossover_strategy_init(self):
        """Test MovingAverageCrossOverStrategy initialization."""
        strategy = MovingAverageCrossOverStrategy()
        strategy.data = MagicMock()
        strategy.data.Close = self.test_data['Close'].values
        
        # Mock I() method for indicators
        with patch.object(strategy, 'I') as mock_I:
            mock_I.return_value = np.array([100, 101, 102])
            strategy.init()
        
        # Strategy should have short and long window attributes
        self.assertTrue(hasattr(strategy, 'short_window'))
        self.assertTrue(hasattr(strategy, 'long_window'))
    
    def test_bollinger_bands_strategy_init(self):
        """Test BollingerBandsStrategy initialization."""
        strategy = BollingerBandsStrategy()
        strategy.data = MagicMock()
        strategy.data.Close = self.test_data['Close'].values
        
        with patch.object(strategy, 'I') as mock_I:
            mock_I.return_value = np.array([100, 101, 102])
            strategy.init()
        
        self.assertTrue(hasattr(strategy, 'period'))
        self.assertTrue(hasattr(strategy, 'num_std'))
    
    def test_macd_strategy_init(self):
        """Test MACDStrategy initialization."""
        strategy = MACDStrategy()
        strategy.data = MagicMock()
        strategy.data.Close = self.test_data['Close'].values
        
        with patch.object(strategy, 'I') as mock_I:
            mock_I.return_value = np.array([100, 101, 102])
            strategy.init()
        
        self.assertTrue(hasattr(strategy, 'fast_period'))
        self.assertTrue(hasattr(strategy, 'slow_period'))
        self.assertTrue(hasattr(strategy, 'signal_period'))
    
    def test_vwap_reversion_strategy_init(self):
        """Test VWAPReversionStrategy initialization."""
        strategy = VWAPReversionStrategy()
        strategy.data = MagicMock()
        strategy.data.Close = self.test_data['Close'].values
        strategy.data.High = self.test_data['High'].values
        strategy.data.Low = self.test_data['Low'].values
        strategy.data.Volume = self.test_data['Volume'].values
        
        strategy.init()
        
        self.assertTrue(hasattr(strategy, 'deviation_pct'))
        self.assertTrue(hasattr(strategy, 'vwap'))
        self.assertIsInstance(strategy.vwap, list)
    
    def test_strategy_parameter_validation(self):
        """Test strategy parameter validation."""
        # Test with invalid parameters
        with self.assertRaises(ValueError):
            strategy = MovingAverageCrossOverStrategy()
            strategy.short_window = -1
            strategy.validate_parameters()
        
        # Test with valid parameters
        strategy = MovingAverageCrossOverStrategy()
        strategy.short_window = 10
        strategy.long_window = 50
        strategy.validate_parameters()  # Should not raise
    
    def test_strategy_inherits_from_base(self):
        """Test that strategies inherit from BaseStrategy."""
        strategies = [
            MovingAverageCrossOverStrategy,
            BollingerBandsStrategy,
            MACDStrategy,
            VWAPReversionStrategy
        ]
        
        from src.strategy.base import BaseStrategy
        
        for strategy_class in strategies:
            self.assertTrue(issubclass(strategy_class, BaseStrategy))
            # Check that common methods exist
            strategy = strategy_class()
            self.assertTrue(hasattr(strategy, 'apply_risk_management'))
            self.assertTrue(hasattr(strategy, 'get_position_size'))
            self.assertTrue(hasattr(strategy, 'validate_parameters'))


if __name__ == '__main__':
    unittest.main()

