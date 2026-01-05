"""
Database Ingestion Module
Provides idempotent insert functions for bars, quotes, and trades.
Uses ON CONFLICT to prevent duplicate data when re-running ingestion.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

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

