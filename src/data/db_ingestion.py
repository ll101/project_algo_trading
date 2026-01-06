"""
Database Ingestion Module
Provides idempotent insert functions for bars, quotes, and trades.
Uses ON CONFLICT to prevent duplicate data when re-running ingestion.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from io import StringIO

import pandas as pd
import requests

from .db_connection import get_db_connection

logger = logging.getLogger(__name__)


def insert_bars_idempotent(bars_data: List[Dict[str, Any]]) -> int:
    """
    Insert bars data idempotently.
    If a bar with the same (time, stock_id) already exists, it will be skipped.
    
    Args:
        bars_data: List of dictionaries with keys: stock_id, time, open, high, low, close, volume, vwap
    
    Returns:
        Number of rows inserted (excluding conflicts)
    """
    if not bars_data:
        return 0
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO trading.bars (stock_id, time, open, high, low, close, volume, vwap)
                VALUES (%(stock_id)s, %(time)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, %(vwap)s)
                ON CONFLICT (time, stock_id) DO NOTHING
            """
            
            cursor.executemany(insert_query, bars_data)
            rows_inserted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Inserted {rows_inserted} bars (skipped duplicates)")
            return rows_inserted
    except Exception as e:
        logger.error(f"Error inserting bars: {e}")
        raise


def insert_quotes_idempotent(quotes_data: List[Dict[str, Any]]) -> int:
    """
    Insert quotes data idempotently.
    If a quote with the same (time, stock_id, bid_price, bid_size, ask_price, ask_size, 
    bid_exchange, ask_exchange, tape) already exists, it will be skipped.
    
    Args:
        quotes_data: List of dictionaries with keys: stock_id, time, bid_price, bid_size,
                    bid_exchange, ask_price, ask_size, ask_exchange, conditions, tape
    
    Returns:
        Number of rows inserted (excluding conflicts)
    """
    if not quotes_data:
        return 0
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO trading.quotes (
                    stock_id, time, bid_price, bid_size, bid_exchange,
                    ask_price, ask_size, ask_exchange, conditions, tape
                )
                VALUES (
                    %(stock_id)s, %(time)s, %(bid_price)s, %(bid_size)s, %(bid_exchange)s,
                    %(ask_price)s, %(ask_size)s, %(ask_exchange)s, %(conditions)s, %(tape)s
                )
                ON CONFLICT (time, stock_id, bid_price, bid_size, ask_price, ask_size, 
                            bid_exchange, ask_exchange, tape) DO NOTHING
            """
            
            cursor.executemany(insert_query, quotes_data)
            rows_inserted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Inserted {rows_inserted} quotes (skipped duplicates)")
            return rows_inserted
    except Exception as e:
        logger.error(f"Error inserting quotes: {e}")
        raise


def insert_trades_idempotent(trades_data: List[Dict[str, Any]]) -> int:
    """
    Insert trades data idempotently.
    If a trade with the same (time, stock_id, trade_id) already exists, it will be skipped.
    Schema matches Alpaca API: c (conditions), i (trade_id), p (price), s (size),
    t (time), x (exchange), z (tape)
    
    Args:
        trades_data: List of dictionaries with keys: stock_id, trade_id, time, price, size,
                    conditions, exchange, tape
    
    Returns:
        Number of rows inserted (excluding conflicts)
    """
    if not trades_data:
        return 0
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO trading.trades (
                    stock_id, trade_id, time, price, size, conditions, exchange, tape
                )
                VALUES (
                    %(stock_id)s, %(trade_id)s, %(time)s, %(price)s, %(size)s,
                    %(conditions)s, %(exchange)s, %(tape)s
                )
                ON CONFLICT (time, stock_id, trade_id) DO NOTHING
            """
            
            cursor.executemany(insert_query, trades_data)
            rows_inserted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Inserted {rows_inserted} trades (skipped duplicates)")
            return rows_inserted
    except Exception as e:
        logger.error(f"Error inserting trades: {e}")
        raise


def fetch_nasdaq100_tickers() -> List[Tuple[str, str]]:
    """
    Fetch Nasdaq-100 ticker symbols and company names from Wikipedia.
    
    Returns:
        List of tuples (symbol, company_name)
    
    Raises:
        Exception: If unable to fetch or parse data from Wikipedia
    """
    try:
        logger.info("Fetching Nasdaq-100 tickers from Wikipedia...")
        
        # Add User-Agent header to avoid 403 Forbidden error
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get('https://en.wikipedia.org/wiki/Nasdaq-100', headers=headers, timeout=10)
        response.raise_for_status()
        
        # Read HTML tables from the response
        tables = pd.read_html(StringIO(response.text))
        
        # The Nasdaq-100 table is typically the 4th table (index 4)
        # Extract ticker symbols and company names
        if len(tables) < 5:
            raise ValueError("Expected at least 5 tables in Wikipedia page, got fewer")
        
        nasdaq_table = tables[4]
        symbols = nasdaq_table['Ticker'].tolist()
        companies = nasdaq_table['Company'].tolist()
        
        # Create list of tuples
        tickers = list(zip(symbols, companies))
        
        logger.info(f"Successfully fetched {len(tickers)} Nasdaq-100 tickers")
        return tickers
        
    except requests.RequestException as e:
        logger.error(f"Error fetching data from Wikipedia: {e}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing Wikipedia table: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching Nasdaq-100 tickers: {e}")
        raise


def get_or_create_stock(symbol: str, company_name: str) -> int:
    """
    Get stock id if exists, or create new stock entry.
    Idempotent - returns existing id if stock already exists.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        company_name: Company name
    
    Returns:
        Stock id (integer)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Try to get existing stock
            cursor.execute(
                "SELECT id FROM trading.stock WHERE symbol = %s",
                (symbol,)
            )
            result = cursor.fetchone()
            
            if result:
                stock_id = result[0]
                logger.debug(f"Stock {symbol} already exists with id {stock_id}")
                return stock_id
            
            # Create new stock
            cursor.execute(
                """
                INSERT INTO trading.stock (symbol, company_name)
                VALUES (%s, %s)
                ON CONFLICT (symbol) DO UPDATE SET company_name = EXCLUDED.company_name
                RETURNING id
                """,
                (symbol, company_name)
            )
            stock_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"Created/updated stock {symbol} with id {stock_id}")
            return stock_id
    except Exception as e:
        logger.error(f"Error getting/creating stock {symbol}: {e}")
        raise


def insert_nasdaq100_stocks() -> Dict[str, int]:
    """
    Fetch Nasdaq-100 tickers from Wikipedia and insert/update them in the database.
    Idempotent - existing stocks will be updated if company name changed.
    
    Returns:
        Dictionary mapping symbol to stock_id for all inserted/updated stocks
    
    Raises:
        Exception: If unable to fetch tickers or insert into database
    """
    try:
        # Fetch tickers from Wikipedia
        tickers = fetch_nasdaq100_tickers()
        
        if not tickers:
            logger.warning("No tickers fetched from Wikipedia")
            return {}
        
        # Insert/update stocks in database
        stock_ids = {}
        inserted_count = 0
        updated_count = 0
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for symbol, company_name in tickers:
                # Check if stock exists
                cursor.execute(
                    "SELECT id FROM trading.stock WHERE symbol = %s",
                    (symbol,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Stock exists - update if company name changed
                    stock_id = result[0]
                    cursor.execute(
                        """
                        UPDATE trading.stock 
                        SET company_name = %s 
                        WHERE symbol = %s AND company_name != %s
                        """,
                        (company_name, symbol, company_name)
                    )
                    if cursor.rowcount > 0:
                        updated_count += 1
                        logger.debug(f"Updated stock {symbol}: {company_name}")
                    stock_ids[symbol] = stock_id
                else:
                    # Insert new stock
                    cursor.execute(
                        """
                        INSERT INTO trading.stock (symbol, company_name)
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        (symbol, company_name)
                    )
                    stock_id = cursor.fetchone()[0]
                    stock_ids[symbol] = stock_id
                    inserted_count += 1
                    logger.debug(f"Inserted stock {symbol}: {company_name}")
            
            conn.commit()
        
        logger.info(f"Nasdaq-100 stocks processed: {inserted_count} inserted, {updated_count} updated, {len(stock_ids)} total")
        return stock_ids
        
    except Exception as e:
        logger.error(f"Error inserting Nasdaq-100 stocks: {e}")
        raise

