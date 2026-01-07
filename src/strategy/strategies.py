"""
Trading Strategies
Implementation of various trend-following trading strategies.
All strategies inherit from BaseStrategy for common functionality.
"""

from typing import Optional
from backtesting.lib import crossover
from pathlib import Path
import sys
import logging
import numpy as np

# Add project root to path for imports when running as script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.strategy.base import BaseStrategy
from src.strategy.indicators import sma, ema, bollinger_bands, macd, rsi, atr, vwap

logger = logging.getLogger(__name__)



class MovingAverageCrossOverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.
    
    Buy when short MA crosses above long MA (golden cross).
    Sell when short MA crosses below long MA (death cross).
    
    Parameters:
        short_window: Period for short moving average (default: 5)
        long_window: Period for long moving average (default: 100)
        ma_type: Type of moving average - 'sma' or 'ema' (default: 'ema')
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Optional take profit percentage
    """
    
    short_window: int = 5
    long_window: int = 100
    ma_type: str = 'ema'
    stop_loss_pct: float = 0.02
    take_profit_pct: Optional[float] = None
    
    def init(self):
        """Initialize indicators."""
        close = self.data.Close
        
        # Validate parameters
        if self.short_window >= self.long_window:
            raise ValueError(f"short_window ({self.short_window}) must be less than long_window ({self.long_window})")
        
        # Define indicators based on MA type
        if self.ma_type.lower() == "ema":
            self.ma_short = self.I(ema, close, self.short_window)
            self.ma_long = self.I(ema, close, self.long_window)
        elif self.ma_type.lower() == "sma":
            self.ma_short = self.I(sma, close, self.short_window)
            self.ma_long = self.I(sma, close, self.long_window)
        else:
            raise ValueError(f"ma_type must be 'sma' or 'ema', got {self.ma_type}")
    
    def next(self):
        """Execute strategy logic."""
        # Apply risk management (stop loss, take profit)
        self.apply_risk_management()
        
        # Entry signal: golden cross (short MA crosses above long MA)
        if crossover(self.ma_short, self.ma_long):
            self.buy()
        
        # Exit signal: death cross (short MA crosses below long MA)
        if crossover(self.ma_long, self.ma_short):
            self.position.close()

class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy.
    
    Buy when price touches lower band (oversold).
    Sell when price reaches middle band or upper band.
    
    Parameters:
        period: Period for Bollinger Bands calculation (default: 20)
        devfactor: Standard deviation multiplier (default: 2.0)
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Optional take profit percentage
    """
    
    period: int = 20
    devfactor: float = 2.0
    stop_loss_pct: float = 0.02
    take_profit_pct: Optional[float] = None
    
    def init(self):
        """Initialize indicators."""
        close = self.data.Close
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            bollinger_bands, close, self.period, self.devfactor, self.devfactor, matype=0
        )
    
    def next(self):
        """Execute strategy logic."""
        # Apply risk management
        self.apply_risk_management()
        
        price = self.data.Close[-1]
        
        # No open position - look for entry
        if not self.position:
            # Long entry: price touches lower band (oversold)
            if price <= self.bb_lower[-1]:
                self.buy()
        
        # Long exit: price reaches middle band
        elif self.position.is_long:
            if price >= self.bb_middle[-1]:
                self.position.close()

class MACDStrategy(BaseStrategy):
    """
    MACD (Moving Average Convergence Divergence) Strategy.
    
    Buy when MACD line crosses above signal line.
    Sell when MACD line crosses below signal line.
    
    Parameters:
        fastperiod: Fast EMA period (default: 12)
        slowperiod: Slow EMA period (default: 50)
        signalperiod: Signal line EMA period (default: 9)
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Optional take profit percentage
    """
    
    fastperiod: int = 12
    slowperiod: int = 50
    signalperiod: int = 9
    stop_loss_pct: float = 0.02
    take_profit_pct: Optional[float] = None
    
    def init(self):
        """Initialize indicators."""
        close = self.data.Close
        self.macd, self.macd_signal, self.macd_hist = self.I(
            macd, close, self.fastperiod, self.slowperiod, self.signalperiod
        )
    
    def next(self):
        """Execute strategy logic."""
        # Apply risk management
        self.apply_risk_management()
        
        # Entry signal: MACD crosses above signal line
        if crossover(self.macd, self.macd_signal):
            self.buy()
        
        # Exit signal: MACD crosses below signal line
        if crossover(self.macd_signal, self.macd):
            self.position.close()



class VWAPReversionStrategy(BaseStrategy):
    """
    VWAP Reversion Strategy.
    
    Mean reversion strategy that trades against VWAP:
    - Buy when price is significantly below VWAP (oversold)
    - Sell when price is significantly above VWAP (overbought)
    
    Parameters:
        deviation_pct: Percentage deviation from VWAP to trigger entry (default: 0.01 = 1%)
        stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
        take_profit_pct: Optional take profit percentage
    """
    
    deviation_pct: float = 0.01  # 1% deviation from VWAP
    stop_loss_pct: float = 0.02
    take_profit_pct: Optional[float] = None
    
    def init(self):
        """Initialize indicators."""
        # VWAP requires high, low, close, and volume
        # Calculate VWAP directly since self.I() expects functions that take single arrays
        # We'll store it as a numpy array and access it directly
        import numpy as np
        
        high = np.array(self.data.High)
        low = np.array(self.data.Low)
        close = np.array(self.data.Close)
        volume = np.array(self.data.Volume)
        
        # Calculate VWAP values
        vwap_values = vwap(high, low, close, volume)
        
        # Store as attribute - we'll access it directly in next()
        # Convert to list for easier indexing
        self.vwap = list(vwap_values)
    
    def next(self):
        """Execute strategy logic."""
        # Apply risk management
        self.apply_risk_management()
        
        # Check if we have enough data
        if len(self.vwap) == 0 or len(self.data.Close) == 0:
            return
        
        # Get current index (backtesting library provides this)
        current_idx = len(self.data.Close) - 1
        
        # Check bounds
        if current_idx < 0 or current_idx >= len(self.vwap):
            return
        
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[current_idx]
        
        # Avoid division by zero or invalid values
        if current_vwap <= 0 or not np.isfinite(current_vwap):
            return
        
        # Calculate deviation from VWAP
        deviation = (current_price - current_vwap) / current_vwap
        
        # No open position - look for entry
        if not self.position:
            # Long entry: price is significantly below VWAP (oversold)
            if deviation < -self.deviation_pct:
                self.buy()
        
        # Long exit: price is significantly above VWAP (overbought) or back to VWAP
        elif self.position.is_long:
            if deviation > self.deviation_pct or deviation >= 0:
                self.position.close()
        