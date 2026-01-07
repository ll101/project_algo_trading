"""
Data Loader Module
Abstracts data fetching from TimescaleDB for backtesting purposes.
Provides functions to load bars data in formats compatible with the backtesting library.
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv

# Add project root to path for imports when running as script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data.db_connection import get_db_connection

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_bars_from_db(
    symbol: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    #timeframe: str = '1min',
    resample: Optional[str] = None
) -> pd.DataFrame:
    """
    Load bars data from TimescaleDB for a single symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        start_date: Start date (string 'YYYY-MM-DD' or datetime)
        end_date: End date (string 'YYYY-MM-DD' or datetime)
        timeframe: Original timeframe of data ('1min', '5min', '1hour', '1day')
                   Used for validation, not filtering
        resample: Optional resampling rule (e.g., '1H', '1D') to aggregate minute data
    
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        Index: DatetimeIndex (timezone-aware UTC)
        Compatible with backtesting library format
    
    Raises:
        ValueError: If symbol not found or date range invalid
        ConnectionError: If database connection fails
    """
    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # Ensure timezone-aware (assume UTC if naive)
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=pd.Timestamp.now().tz)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=pd.Timestamp.now().tz)
    
    # Validate date range
    if start_date >= end_date:
        raise ValueError(f"start_date ({start_date}) must be before end_date ({end_date})")
    
    logger.info(f"Loading bars for {symbol} from {start_date.date()} to {end_date.date()}")
    
    query = """
        SELECT 
            b.time,
            b.open,
            b.high,
            b.low,
            b.close,
            b.volume
        FROM trading.bars b
        JOIN trading.stock s ON b.stock_id = s.id
        WHERE s.symbol = %s
        AND b.time >= %s
        AND b.time <= %s
        ORDER BY b.time ASC
    """
    
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, start_date, end_date),
                parse_dates=['time']
            )
        
        if df.empty:
            logger.warning(f"No data found for {symbol} in date range {start_date} to {end_date}")
            return _create_empty_bars_dataframe()
        
        # Set time as index
        df.set_index('time', inplace=True)
        
        # Rename columns to match backtesting library format (capitalize first letter)
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Ensure timezone-aware index (UTC)
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        
        # Resample if requested
        if resample:
            df = _resample_bars(df, resample)
            df.dropna(inplace=True)
        
        # Validate data quality
        validate_data_quality(df, symbol)
        
        logger.info(f"Loaded {len(df)} bars for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading bars for {symbol}: {e}")
        raise


def load_multiple_symbols(
    symbols: List[str],
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    timeframe: str = '1min',
    resample: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    """
    Load bars data for multiple symbols.
    
    Args:
        symbols: List of stock symbols
        start_date: Start date (string 'YYYY-MM-DD' or datetime)
        end_date: End date (string 'YYYY-MM-DD' or datetime)
        timeframe: Original timeframe of data
        resample: Optional resampling rule
    
    Returns:
        Dictionary mapping symbol to DataFrame
        Each DataFrame has same format as load_bars_from_db()
    
    Raises:
        ValueError: If no symbols provided or date range invalid
    """
    if not symbols:
        raise ValueError("symbols list cannot be empty")
    
    logger.info(f"Loading data for {len(symbols)} symbols")
    
    result = {}
    for symbol in symbols:
        try:
            df = load_bars_from_db(symbol, start_date, end_date, timeframe, resample)
            result[symbol] = df
        except Exception as e:
            logger.warning(f"Failed to load data for {symbol}: {e}")
            # Continue with other symbols
            continue
    
    logger.info(f"Successfully loaded data for {len(result)}/{len(symbols)} symbols")
    return result


@lru_cache(maxsize=128)
def get_available_symbols() -> List[str]:
    """
    Get list of all available symbols in the database.
    
    Returns:
        List of stock symbols (sorted alphabetically)
    
    Note:
        Results are cached for performance.
        Use get_available_symbols.cache_clear() to refresh.
    """
    query = """
        SELECT DISTINCT s.symbol
        FROM trading.stock s
        WHERE EXISTS (
            SELECT 1 FROM trading.bars b
            WHERE b.stock_id = s.id
        )
        ORDER BY s.symbol
    """
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            symbols = [row[0] for row in cursor.fetchall()]
            cursor.close()
        
        logger.info(f"Found {len(symbols)} symbols with data in database")
        return symbols
        
    except Exception as e:
        logger.error(f"Error fetching available symbols: {e}")
        raise


def get_symbol_data_range(symbol: str) -> Dict[str, datetime]:
    """
    Get the date range of available data for a symbol.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Dictionary with 'start_date' and 'end_date' keys
        Returns None for both if symbol not found or has no data
    """
    query = """
        SELECT 
            MIN(b.time) as start_date,
            MAX(b.time) as end_date
        FROM trading.bars b
        JOIN trading.stock s ON b.stock_id = s.id
        WHERE s.symbol = %s
    """
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (symbol,))
            row = cursor.fetchone()
            cursor.close()
        
        if row and row[0] and row[1]:
            return {
                'start_date': row[0],
                'end_date': row[1]
            }
        else:
            logger.warning(f"No data found for symbol {symbol}")
            return {'start_date': None, 'end_date': None}
            
    except Exception as e:
        logger.error(f"Error fetching data range for {symbol}: {e}")
        raise


def validate_data_quality(
    df: pd.DataFrame,
    symbol: str = "Unknown",
    max_gap_hours: float = 24.0,
    min_data_points: int = 10
) -> Dict[str, Union[bool, int, float, List]]:
    """
    Validate data quality of loaded bars.
    
    Args:
        df: DataFrame with bars data (must have DatetimeIndex)
        symbol: Symbol name for logging
        max_gap_hours: Maximum acceptable gap in hours (default: 24 hours)
        min_data_points: Minimum number of data points required
    
    Returns:
        Dictionary with validation results:
        - 'is_valid': bool
        - 'total_rows': int
        - 'missing_values': dict of column -> count
        - 'gaps': list of gap periods
        - 'gap_count': int
        - 'duplicate_timestamps': int
        - 'warnings': list of warning messages
    """
    if df.empty:
        logger.warning(f"DataFrame for {symbol} is empty")
        return {
            'is_valid': False,
            'total_rows': 0,
            'missing_values': {},
            'gaps': [],
            'gap_count': 0,
            'duplicate_timestamps': 0,
            'warnings': ['DataFrame is empty']
        }
    
    results = {
        'is_valid': True,
        'total_rows': len(df),
        'missing_values': {},
        'gaps': [],
        'gap_count': 0,
        'duplicate_timestamps': 0,
        'warnings': []
    }
    
    # Check minimum data points
    if len(df) < min_data_points:
        results['is_valid'] = False
        results['warnings'].append(
            f"Only {len(df)} data points, minimum required: {min_data_points}"
        )
    
    # Check for missing values
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                results['missing_values'][col] = int(missing_count)
                results['warnings'].append(f"Missing values in {col}: {missing_count}")
                results['is_valid'] = False
    
    # Check for duplicate timestamps
    duplicate_count = df.index.duplicated().sum()
    if duplicate_count > 0:
        results['duplicate_timestamps'] = int(duplicate_count)
        results['warnings'].append(f"Duplicate timestamps: {duplicate_count}")
        results['is_valid'] = False
    
    # Check for gaps in time series
    if len(df) > 1:
        time_diffs = df.index.to_series().diff()
        # Convert to hours
        gaps = time_diffs[time_diffs > pd.Timedelta(hours=max_gap_hours)]
        
        if len(gaps) > 0:
            results['gap_count'] = len(gaps)
            results['gaps'] = [
                {
                    'start': df.index[i-1] if i > 0 else None,
                    'end': df.index[i],
                    'duration_hours': gap.total_seconds() / 3600
                }
                for i, gap in enumerate(gaps, start=1)
            ]
            results['warnings'].append(
                f"Found {len(gaps)} gaps larger than {max_gap_hours} hours"
            )
            # Gaps are warnings, not necessarily invalid
    
    # Check for invalid OHLC relationships
    invalid_ohlc = (
        (df['High'] < df['Low']) |
        (df['High'] < df['Open']) |
        (df['High'] < df['Close']) |
        (df['Low'] > df['Open']) |
        (df['Low'] > df['Close'])
    )
    invalid_count = invalid_ohlc.sum()
    if invalid_count > 0:
        results['is_valid'] = False
        results['warnings'].append(
            f"Invalid OHLC relationships: {invalid_count} rows"
        )
    
    # Check for negative or zero volume
    if 'Volume' in df.columns:
        invalid_volume = (df['Volume'] <= 0).sum()
        if invalid_volume > 0:
            results['warnings'].append(
                f"Invalid volume (<=0): {invalid_volume} rows"
            )
    
    # Log warnings
    if results['warnings']:
        logger.warning(f"Data quality issues for {symbol}: {', '.join(results['warnings'])}")
    else:
        logger.info(f"Data quality check passed for {symbol}")
    
    return results


def _resample_bars(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """
    Resample minute-level bars to a different timeframe.
    
    Args:
        df: DataFrame with bars data
        rule: Pandas resampling rule (e.g., '1H', '1D', '5min')
    
    Returns:
        Resampled DataFrame with OHLCV aggregation
    """
    if df.empty:
        return df
    
    # Resample with OHLC aggregation
    resampled = df.resample(rule).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    
    # Drop rows where all values are NaN (e.g., weekends for daily resampling)
    resampled = resampled.dropna(how='all')
    
    logger.info(f"Resampled {len(df)} bars to {len(resampled)} bars using rule '{rule}'")
    return resampled


def _create_empty_bars_dataframe() -> pd.DataFrame:
    """
    Create an empty DataFrame with the correct structure for bars data.
    
    Returns:
        Empty DataFrame with columns: Open, High, Low, Close, Volume
        Index: Empty DatetimeIndex (timezone-aware UTC)
    """
    return pd.DataFrame(
        columns=['Open', 'High', 'Low', 'Close', 'Volume'],
        index=pd.DatetimeIndex([], tz='UTC', name='time')
    )


def load_bars_for_backtest(
    symbol: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    resample: Optional[str] = None
) -> pd.DataFrame:
    """
    Convenience function to load bars in format ready for backtesting library.
    
    This is an alias for load_bars_from_db() with backtesting-specific defaults.
    Ensures data is in the exact format expected by the backtesting library.
    
    Args:
        symbol: Stock symbol
        start_date: Start date
        end_date: End date
        timeframe: Timeframe string (for logging/validation)
    
    Returns:
        DataFrame compatible with backtesting library
    """
    df = load_bars_from_db(symbol, start_date, end_date, resample=resample)
    
    # Ensure index name is set (backtesting library may expect this)
    if df.index.name != 'time':
        df.index.name = 'time'
    
    return df


# Example usage and testing
if __name__ == "__main__":
    # Example: Load data for a symbol
    try:
        # Get available symbols
        symbols = get_available_symbols()
        print(f"Available symbols: {symbols[:10]}...")  # Show first 10
        
        if symbols:
            # Load data for first symbol
            test_symbol = symbols[0]
            print(f"\nLoading data for {test_symbol}...")
            
            # Get data range
            date_range = get_symbol_data_range(test_symbol)
            print(f"Data range: {date_range}")
            
            if date_range['start_date'] and date_range['end_date']:
                # Load last 30 days
                end_date = date_range['end_date']
                start_date = end_date - timedelta(days=30)
                
                df = load_bars_for_backtest(
                    test_symbol,
                    start_date,
                    end_date
                )
                
                print(f"\nLoaded {len(df)} bars")
                print(f"Date range: {df.index.min()} to {df.index.max()}")
                print(f"\nFirst few rows:")
                print(df.head())
                
                # Validate data quality
                validation = validate_data_quality(df, test_symbol, max_gap_hours=72)
                print(f"\nData quality validation:")
                print(f"Valid: {validation['is_valid']}")
                print(f"Warnings: {len(validation['warnings'])}")
                if validation['warnings']:
                    for warning in validation['warnings']:
                        print(f"  - {warning}")
        
    except Exception as e:
        logger.error(f"Error in example usage: {e}")
        import traceback
        traceback.print_exc()

