"""
Alpaca API Data Ingestion Script
Ingests stocks first, then bars, quotes, and trades from Alpaca API.
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv

# Add project root to path for imports when running as script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest, StockTradesRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from src.data.db_ingestion import (
    insert_nasdaq100_stocks,
    get_or_create_stock,
    insert_bars_idempotent,
    insert_quotes_idempotent,
    insert_trades_idempotent,
)
from src.data.db_connection import test_connection

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_alpaca_client():
    """
    Initialize and return Alpaca API client.
    
    Returns:
        StockHistoricalDataClient instance
    
    Raises:
        ValueError: If API credentials are not set
    """
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        raise ValueError(
            "Alpaca API credentials not found. Please set ALPACA_API_KEY and "
            "ALPACA_SECRET_KEY in your .env file"
        )
    
    client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
    logger.info("Alpaca API client initialized")
    return client


def prepare_bars_dataframe(df: pd.DataFrame, stock_id: int) -> List[Dict[str, Any]]:
    """
    Prepare bars DataFrame for database insertion.
    
    Args:
        df: DataFrame from Alpaca API response (.df)
        stock_id: Stock ID from database
    
    Returns:
        List of dictionaries for database insertion
    """
    if df.empty:
        return []
    
    # Reset index to get symbol and timestamp as columns (MultiIndex: [symbol, timestamp])
    # If MultiIndex, reset both levels; otherwise just reset
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index(level=[0, 1])
    else:
        df = df.reset_index()
    
    # Drop symbol column if present (we use stock_id instead)
    if 'symbol' in df.columns:
        df = df.drop('symbol', axis=1)
    
    # Drop trade_count if present (not in our schema)
    if 'trade_count' in df.columns:
        df = df.drop('trade_count', axis=1)
    
    # Rename timestamp to time
    if 'timestamp' in df.columns:
        df = df.rename(columns={'timestamp': 'time'})
    
    # Add stock_id column
    df['stock_id'] = stock_id
    
    # Convert to list of dictionaries
    return df.to_dict('records')


def prepare_quotes_dataframe(df: pd.DataFrame, stock_id: int) -> List[Dict[str, Any]]:
    """
    Prepare quotes DataFrame for database insertion.
    
    Args:
        df: DataFrame from Alpaca API response (.df)
        stock_id: Stock ID from database
    
    Returns:
        List of dictionaries for database insertion
    """
    if df.empty:
        return []
    
    # Reset index to get symbol and timestamp as columns (MultiIndex: [symbol, timestamp])
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index(level=[0, 1])
    else:
        df = df.reset_index()
    
    # Drop symbol column if present
    if 'symbol' in df.columns:
        df = df.drop('symbol', axis=1)
    
    # Rename timestamp to time
    if 'timestamp' in df.columns:
        df = df.rename(columns={'timestamp': 'time'})
    
    # Handle conditions column - convert to list if it's not already
    if 'conditions' in df.columns:
        df['conditions'] = df['conditions'].apply(
            lambda x: list(x) if isinstance(x, (list, tuple)) else ([x] if pd.notna(x) else [])
        )
    else:
        df['conditions'] = [[]] * len(df)
    
    # Add stock_id column
    df['stock_id'] = stock_id
    
    # Convert to list of dictionaries
    return df.to_dict('records')


def prepare_trades_dataframe(df: pd.DataFrame, stock_id: int) -> List[Dict[str, Any]]:
    """
    Prepare trades DataFrame for database insertion.
    
    Args:
        df: DataFrame from Alpaca API response (.df)
        stock_id: Stock ID from database
    
    Returns:
        List of dictionaries for database insertion
    """
    if df.empty:
        return []
    
    # Reset index to get symbol and timestamp as columns (MultiIndex: [symbol, timestamp])
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index(level=[0, 1])
    else:
        df = df.reset_index()
    
    # Drop symbol column if present
    if 'symbol' in df.columns:
        df = df.drop('symbol', axis=1)
    
    # Rename timestamp to time
    if 'timestamp' in df.columns:
        df = df.rename(columns={'timestamp': 'time'})
    
    # Rename id to trade_id
    if 'id' in df.columns:
        df = df.rename(columns={'id': 'trade_id'})
    elif 'trade_id' not in df.columns:
        logger.warning("No trade_id column found in trades DataFrame")
        return []
    
    # Handle conditions column - convert to list if it's not already
    if 'conditions' in df.columns:
        df['conditions'] = df['conditions'].apply(
            lambda x: list(x) if isinstance(x, (list, tuple)) else ([x] if pd.notna(x) else [])
        )
    else:
        df['conditions'] = [[]] * len(df)
    
    # Add stock_id column
    df['stock_id'] = stock_id
    
    # Filter out rows with None trade_id
    df = df[df['trade_id'].notna()]
    
    # Convert to list of dictionaries
    return df.to_dict('records')


def ingest_bars_for_symbol(
    client: StockHistoricalDataClient,
    symbol: str,
    stock_id: int,
    start_date: datetime,
    end_date: datetime,
    timeframe: TimeFrame = TimeFrame(1, TimeFrameUnit.Minute),
    check_existing: bool = True,
) -> int:
    """
    Ingest bars data for a single symbol using DataFrame.
    
    Args:
        client: Alpaca API client
        symbol: Stock symbol
        stock_id: Stock ID from database
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
        timeframe: Timeframe for bars (default: 1 minute)
        check_existing: If True, check existing data and skip if already complete
    
    Returns:
        Number of bars inserted
    """
    from src.data.db_ingestion import (
        should_skip_symbol,
        get_effective_start_date
    )
    
    try:
        # Check if we should skip this symbol
        if check_existing:
            if should_skip_symbol(symbol, end_date, table='bars'):
                return 0
            
            # Get effective start date (from last existing timestamp if any)
            effective_start = get_effective_start_date(symbol, start_date, table='bars')
            
            # If effective start is after end_date, nothing to ingest
            if effective_start >= end_date:
                logger.info(f"Symbol {symbol} already has complete bars data up to {end_date}")
                return 0
            
            start_date = effective_start
        
        logger.info(f"Fetching bars for {symbol} from {start_date.date()} to {end_date.date()}")
        
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=start_date,
            end=end_date,
        )
        
        # Get DataFrame directly from API response
        bars_df = client.get_stock_bars(request).df
        
        if bars_df.empty:
            logger.warning(f"No bars data found for {symbol}")
            return 0
        
        # Prepare data for database insertion
        bars_data = prepare_bars_dataframe(bars_df, stock_id)
        
        if bars_data:
            inserted_count = insert_bars_idempotent(bars_data)
            logger.info(f"Inserted {inserted_count} bars for {symbol}")
            return inserted_count
        else:
            logger.warning(f"No bars data to insert for {symbol}")
            return 0
            
    except Exception as e:
        logger.error(f"Error ingesting bars for {symbol}: {e}")
        raise


def ingest_quotes_for_symbol(
    client: StockHistoricalDataClient,
    symbol: str,
    stock_id: int,
    start_date: datetime,
    end_date: datetime,
    check_existing: bool = True
) -> int:
    """
    Ingest quotes data for a single symbol using DataFrame.
    
    Args:
        client: Alpaca API client
        symbol: Stock symbol
        stock_id: Stock ID from database
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
        check_existing: If True, check existing data and skip if already complete
    
    Returns:
        Number of quotes inserted
    """
    from src.data.db_ingestion import (
        should_skip_symbol,
        get_effective_start_date
    )
    
    try:
        # Check if we should skip this symbol
        if check_existing:
            if should_skip_symbol(symbol, end_date, table='quotes'):
                return 0
            
            # Get effective start date
            effective_start = get_effective_start_date(symbol, start_date, table='quotes')
            
            if effective_start >= end_date:
                logger.info(f"Symbol {symbol} already has complete quotes data up to {end_date}")
                return 0
            
            start_date = effective_start
        
        logger.info(f"Fetching quotes for {symbol} from {start_date.date()} to {end_date.date()}")
        
        request = StockQuotesRequest(
            symbol_or_symbols=symbol,
            start=start_date,
            end=end_date,
        )
        
        # Get DataFrame directly from API response
        quotes_df = client.get_stock_quotes(request).df
        
        if quotes_df.empty:
            logger.warning(f"No quotes data found for {symbol}")
            return 0
        
        # Prepare data for database insertion
        quotes_data = prepare_quotes_dataframe(quotes_df, stock_id)
        
        if quotes_data:
            inserted_count = insert_quotes_idempotent(quotes_data)
            logger.info(f"Inserted {inserted_count} quotes for {symbol}")
            return inserted_count
        else:
            logger.warning(f"No quotes data to insert for {symbol}")
            return 0
            
    except Exception as e:
        logger.error(f"Error ingesting quotes for {symbol}: {e}")
        raise


def ingest_trades_for_symbol(
    client: StockHistoricalDataClient,
    symbol: str,
    stock_id: int,
    start_date: datetime,
    end_date: datetime,
    check_existing: bool = True
) -> int:
    """
    Ingest trades data for a single symbol using DataFrame.
    
    Args:
        client: Alpaca API client
        symbol: Stock symbol
        stock_id: Stock ID from database
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
        check_existing: If True, check existing data and skip if already complete
    
    Returns:
        Number of trades inserted
    """
    from src.data.db_ingestion import (
        should_skip_symbol,
        get_effective_start_date
    )
    
    try:
        # Check if we should skip this symbol
        if check_existing:
            if should_skip_symbol(symbol, end_date, table='trades'):
                return 0
            
            # Get effective start date
            effective_start = get_effective_start_date(symbol, start_date, table='trades')
            
            if effective_start >= end_date:
                logger.info(f"Symbol {symbol} already has complete trades data up to {end_date}")
                return 0
            
            start_date = effective_start
        
        logger.info(f"Fetching trades for {symbol} from {start_date.date()} to {end_date.date()}")
        
        request = StockTradesRequest(
            symbol_or_symbols=symbol,
            start=start_date,
            end=end_date,
        )
        
        # Get DataFrame directly from API response
        trades_df = client.get_stock_trades(request).df
        
        if trades_df.empty:
            logger.warning(f"No trades data found for {symbol}")
            return 0
        
        # Prepare data for database insertion
        trades_data = prepare_trades_dataframe(trades_df, stock_id)
        
        if trades_data:
            inserted_count = insert_trades_idempotent(trades_data)
            logger.info(f"Inserted {inserted_count} trades for {symbol}")
            return inserted_count
        else:
            logger.warning(f"No trades data to insert for {symbol}")
            return 0
            
    except Exception as e:
        logger.error(f"Error ingesting trades for {symbol}: {e}")
        raise


def main(
    start_date: str = "2025-07-01",
    end_date: str = "2025-12-31",
    symbols: List[str] = None
):
    """
    Main ingestion function.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        symbols: List of symbols to ingest. If None, uses all stocks from database.
    """
    logger.info("=" * 60)
    logger.info("Starting Alpaca Data Ingestion")
    logger.info("=" * 60)
    
    # Test database connection
    if not test_connection():
        logger.error("Database connection failed. Please check your setup.")
        return
    
    # Step 1: Ingest stocks first
    logger.info("\nStep 1: Ingesting stock dimension table (Nasdaq-100)...")
    try:
        stock_ids = insert_nasdaq100_stocks()
        logger.info(f"✓ Successfully processed {len(stock_ids)} stocks")
    except Exception as e:
        logger.error(f"Error ingesting stocks: {e}")
        return
    
    # Step 2: Initialize Alpaca client
    logger.info("\nStep 2: Initializing Alpaca API client...")
    try:
        client = get_alpaca_client()
    except Exception as e:
        logger.error(f"Error initializing Alpaca client: {e}")
        return
    
    # Step 3: Parse dates
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1) - timedelta(seconds=1)
    except ValueError as e:
        logger.error(f"Invalid date format. Use YYYY-MM-DD: {e}")
        return
    
    # Step 4: Get symbols to process
    if symbols is None:
        symbols = list(stock_ids.keys())
        logger.info(f"Processing all {len(symbols)} stocks from database")
    else:
        # Get stock_ids for specified symbols
        missing_symbols = []
        for symbol in symbols:
            if symbol not in stock_ids:
                stock_id = get_or_create_stock(symbol, f"{symbol} Corp")
                stock_ids[symbol] = stock_id
        logger.info(f"Processing {len(symbols)} specified symbols")
    
    # Step 5: Ingest market data for each symbol
    logger.info(f"\nStep 3: Ingesting market data from {start_date} to {end_date}...")
    logger.info(f"Timeframe: 1 minute")
    logger.info("Note: Will check existing data and skip symbols that are already up-to-date")
    
    total_bars = 0
    total_quotes = 0
    total_trades = 0
    skipped_symbols = 0
    
    for i, symbol in enumerate(symbols, 1):
        stock_id = stock_ids.get(symbol)
        if stock_id is None:
            logger.warning(f"Stock ID not found for {symbol}, skipping...")
            continue
        
        logger.info(f"\n[{i}/{len(symbols)}] Processing {symbol} (ID: {stock_id})...")
        
        try:
            # Ingest bars (with existing data check)
            bars_count = ingest_bars_for_symbol(
                client, symbol, stock_id, start_dt, end_dt, 
                TimeFrame(1, TimeFrameUnit.Minute), check_existing=True
            )
            total_bars += bars_count
            
            if bars_count == 0:
                skipped_symbols += 1
            
            # Ingest quotes
            # quotes_count = ingest_quotes_for_symbol(
            #     client, symbol, stock_id, start_dt, end_dt
            # )
            # total_quotes += quotes_count
            
            # Ingest trades
            # trades_count = ingest_trades_for_symbol(
            #     client, symbol, stock_id, start_dt, end_dt
            # )
            # total_trades += trades_count
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            continue
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Ingestion Summary")
    logger.info("=" * 60)
    logger.info(f"Stocks processed: {len(symbols)}")
    logger.info(f"Symbols skipped (already up-to-date): {skipped_symbols}")
    logger.info(f"Total bars inserted: {total_bars}")
    # logger.info(f"Total quotes inserted: {total_quotes}")
    # logger.info(f"Total trades inserted: {total_trades}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments if provided
    start_date = sys.argv[1] if len(sys.argv) > 1 else "2025-07-01"
    end_date = sys.argv[2] if len(sys.argv) > 2 else "2025-12-31"
    symbols = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    
    main(start_date=start_date, end_date=end_date, symbols=symbols)

