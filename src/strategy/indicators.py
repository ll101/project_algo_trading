"""
Indicator Utilities
Wrapper functions around talib for consistent indicator calculation.
Provides error handling and parameter validation.
"""

import numpy as np
import talib
import logging

logger = logging.getLogger(__name__)


def sma(close: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Simple Moving Average.
    
    Args:
        close: Array of closing prices
        period: Period for moving average
    
    Returns:
        Array of SMA values
    """
    if period <= 0:
        raise ValueError(f"Period must be positive, got {period}")
    if len(close) < period:
        logger.warning(f"Insufficient data for SMA({period}): {len(close)} values")
    return talib.SMA(close, timeperiod=period)


def ema(close: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Exponential Moving Average.
    
    Args:
        close: Array of closing prices
        period: Period for moving average
    
    Returns:
        Array of EMA values
    """
    if period <= 0:
        raise ValueError(f"Period must be positive, got {period}")
    if len(close) < period:
        logger.warning(f"Insufficient data for EMA({period}): {len(close)} values")
    return talib.EMA(close, timeperiod=period)


def bollinger_bands(
    close: np.ndarray, 
    period: int, 
    nbdevup: float = 2.0, 
    nbdevdn: float = 2.0, 
    matype: int = 0
) -> tuple:
    """
    Calculate Bollinger Bands.
    
    Args:
        close: Array of closing prices
        period: Period for moving average
        nbdevup: Number of standard deviations for upper band
        nbdevdn: Number of standard deviations for lower band
        matype: Moving average type (0=SMA, 1=EMA, etc.)
    
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    if period <= 0:
        raise ValueError(f"Period must be positive, got {period}")
    if len(close) < period:
        logger.warning(f"Insufficient data for Bollinger Bands({period}): {len(close)} values")
    return talib.BBANDS(close, timeperiod=period, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=matype)


def macd(
    close: np.ndarray, 
    fastperiod: int, 
    slowperiod: int, 
    signalperiod: int
) -> tuple:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        close: Array of closing prices
        fastperiod: Fast EMA period
        slowperiod: Slow EMA period
        signalperiod: Signal line EMA period
    
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    if fastperiod >= slowperiod:
        raise ValueError(f"fastperiod ({fastperiod}) must be less than slowperiod ({slowperiod})")
    if len(close) < slowperiod:
        logger.warning(f"Insufficient data for MACD: {len(close)} values")
    return talib.MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Calculate RSI (Relative Strength Index).
    
    Args:
        close: Array of closing prices
        period: Period for RSI calculation (default: 14)
    
    Returns:
        Array of RSI values (0-100)
    """
    if period <= 0:
        raise ValueError(f"Period must be positive, got {period}")
    if len(close) < period + 1:
        logger.warning(f"Insufficient data for RSI({period}): {len(close)} values")
    return talib.RSI(close, timeperiod=period)


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Calculate ATR (Average True Range).
    
    Args:
        high: Array of high prices
        low: Array of low prices
        close: Array of closing prices
        period: Period for ATR calculation (default: 14)
    
    Returns:
        Array of ATR values
    """
    if period <= 0:
        raise ValueError(f"Period must be positive, got {period}")
    if len(high) != len(low) or len(high) != len(close):
        raise ValueError("high, low, and close arrays must have same length")
    if len(high) < period:
        logger.warning(f"Insufficient data for ATR({period}): {len(high)} values")
    return talib.ATR(high, low, close, timeperiod=period)


def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Calculate ADX (Average Directional Index).
    
    Args:
        high: Array of high prices
        low: Array of low prices
        close: Array of closing prices
        period: Period for ADX calculation (default: 14)
    
    Returns:
        Array of ADX values
    """
    if period <= 0:
        raise ValueError(f"Period must be positive, got {period}")
    if len(high) != len(low) or len(high) != len(close):
        raise ValueError("high, low, and close arrays must have same length")
    if len(high) < period:
        logger.warning(f"Insufficient data for ADX({period}): {len(high)} values")
    return talib.ADX(high, low, close, timeperiod=period)


def vwap(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """
    Calculate VWAP (Volume Weighted Average Price).
    
    Note: talib doesn't have a direct VWAP function, this is a simplified version.
    For proper VWAP, you typically need session-based calculation.
    
    Args:
        high: Array of high prices
        low: Array of low prices
        close: Array of closing prices
        volume: Array of volumes
    
    Returns:
        Array of VWAP values
    """
    if len(high) != len(low) or len(high) != len(close) or len(high) != len(volume):
        raise ValueError("high, low, close, and volume arrays must have same length")
    
    # Calculate typical price
    typical_price = (high + low + close) / 3.0
    
    # Calculate VWAP (cumulative)
    cumulative_tpv = np.cumsum(typical_price * volume)
    cumulative_volume = np.cumsum(volume)
    
    # Avoid division by zero
    vwap_values = np.where(cumulative_volume > 0, cumulative_tpv / cumulative_volume, typical_price)
    
    return vwap_values