"""
Tests for base strategy module.
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

from src.strategy.base import BaseStrategy


class TestBaseStrategy(unittest.TestCase):
    """Test cases for BaseStrategy class."""
    
    def test_base_strategy_init(self):
        """Test BaseStrategy initialization."""
        strategy = BaseStrategy()
        strategy.init()
        
        self.assertIsNone(strategy.entry_price)
        self.assertEqual(strategy.stop_loss_pct, 0.02)
        self.assertEqual(strategy.position_size, 1.0)
    
    def test_apply_risk_management_no_position(self):
        """Test risk management with no position."""
        strategy = BaseStrategy()
        strategy.init()
        strategy.position = None
        
        # Should not raise error
        strategy.apply_risk_management()
    
    @patch('src.strategy.base.BaseStrategy.position')
    def test_apply_risk_management_stop_loss(self, mock_position):
        """Test stop loss application."""
        strategy = BaseStrategy()
        strategy.init()
        strategy.stop_loss_pct = 0.02
        strategy.entry_price = 100.0
        
        # Mock position and data
        mock_position.size = 1
        strategy.position = mock_position
        
        # Mock data with price below stop loss
        strategy.data = MagicMock()
        strategy.data.Close = MagicMock()
        strategy.data.Close.__getitem__.return_value = 97.0  # 3% below entry
        
        # Mock sell method
        strategy.sell = MagicMock()
        
        strategy.apply_risk_management()
        
        # Should trigger sell due to stop loss
        strategy.sell.assert_called()
    
    def test_get_position_size(self):
        """Test position sizing calculation."""
        strategy = BaseStrategy()
        strategy.position_size = 0.5  # 50% of equity
        
        # Mock equity
        strategy.equity = 100000
        
        size = strategy.get_position_size()
        self.assertEqual(size, 50000)
    
    def test_validate_parameters(self):
        """Test parameter validation."""
        strategy = BaseStrategy()
        strategy.stop_loss_pct = 0.02
        strategy.take_profit_pct = 0.05
        strategy.position_size = 1.0
        
        # Should not raise error for valid parameters
        strategy.validate_parameters()
        
        # Test invalid stop loss
        strategy.stop_loss_pct = -0.01
        with self.assertRaises(ValueError):
            strategy.validate_parameters()


if __name__ == '__main__':
    unittest.main()

