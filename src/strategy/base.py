"""
Base Strategy Class
Provides common interface and shared functionality for all trading strategies.
"""

from typing import Optional
from backtesting import Strategy
from backtesting.lib import crossover
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(Strategy):
    """
    Base class for all trading strategies.
    
    Provides common functionality:
    - Position sizing
    - Risk management (stop loss, take profit)
    - Common utility methods
    - Standardized parameter handling
    """
    
    # Common risk management parameters
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: Optional[float] = None  # Optional take profit
    position_size: float = 1.0  # Position size as fraction of equity (1.0 = 100%)
    
    def init(self):
        """
        Initialize strategy indicators.
        Override this method in subclasses to set up indicators.
        """
        # Track entry price manually (backtesting library doesn't provide this)
        self.entry_price = None
    
    def next(self):
        """
        Execute strategy logic for each bar.
        Override this method in subclasses to implement trading logic.
        """
        pass
    
    def apply_risk_management(self):
        """
        Apply stop loss and take profit rules.
        Called automatically in next() if position exists.
        """
        if not self.position:
            # Reset entry price when no position
            self.entry_price = None
            return
        
        # Track entry price when position is first detected
        # (backtesting library doesn't provide entry_price attribute)
        if self.entry_price is None:
            # Position exists but we haven't recorded entry price yet
            # Use current price as entry price (will be set on first bar after entry)
            self.entry_price = self.data.Close[-1]
        
        current_price = self.data.Close[-1]
        entry_price = self.entry_price
        
        # Stop loss
        if self.stop_loss_pct and entry_price:
            if self.position.is_long:
                stop_price = entry_price * (1 - self.stop_loss_pct)
                if current_price <= stop_price:
                    logger.debug(f"Stop loss triggered at {current_price:.2f}")
                    self.position.close()
                    self.entry_price = None
                    return
            elif self.position.is_short:
                stop_price = entry_price * (1 + self.stop_loss_pct)
                if current_price >= stop_price:
                    logger.debug(f"Stop loss triggered at {current_price:.2f}")
                    self.position.close()
                    self.entry_price = None
                    return
        
        # Take profit
        if self.take_profit_pct and entry_price:
            if self.position.is_long:
                take_profit_price = entry_price * (1 + self.take_profit_pct)
                if current_price >= take_profit_price:
                    logger.debug(f"Take profit triggered at {current_price:.2f}")
                    self.position.close()
                    self.entry_price = None
                    return
            elif self.position.is_short:
                take_profit_price = entry_price * (1 - self.take_profit_pct)
                if current_price <= take_profit_price:
                    logger.debug(f"Take profit triggered at {current_price:.2f}")
                    self.position.close()
                    self.entry_price = None
                    return
    
    def get_position_size(self) -> float:
        """
        Calculate position size based on equity and position_size parameter.
        
        Returns:
            Position size as fraction of equity
        """
        return self.position_size
    
    def validate_parameters(self):
        """
        Validate strategy parameters.
        Override in subclasses to add parameter validation.
        
        Raises:
            ValueError: If parameters are invalid
        """
        if self.stop_loss_pct < 0 or self.stop_loss_pct > 1:
            raise ValueError(f"stop_loss_pct must be between 0 and 1, got {self.stop_loss_pct}")
        
        if self.position_size <= 0 or self.position_size > 1:
            raise ValueError(f"position_size must be between 0 and 1, got {self.position_size}")
        
        if self.take_profit_pct is not None and (self.take_profit_pct < 0 or self.take_profit_pct > 1):
            raise ValueError(f"take_profit_pct must be between 0 and 1, got {self.take_profit_pct}")

