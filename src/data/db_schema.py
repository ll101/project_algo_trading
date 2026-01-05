"""
Database Schema Module
Handles database schema creation, verification, and TimescaleDB hypertable setup.
"""

import logging
from typing import List, Tuple, Optional

from .db_connection import get_db_connection

logger = logging.getLogger(__name__)


def create_schema(schema_name: str = 'trading') -> bool:
    """
    Create a database schema if it doesn't exist.
    
    Args:
        schema_name: Name of the schema to create
    
    Returns:
        True if schema was created or already exists, False on error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE SCHEMA IF NOT EXISTS {schema_name};"
            )
            conn.commit()
            logger.info(f"Schema '{schema_name}' created or already exists")
            return True
    except Exception as e:
        logger.error(f"Error creating schema '{schema_name}': {e}")
        return False


def enable_timescaledb_extension() -> bool:
    """
    Enable TimescaleDB extension if not already enabled.
    
    Returns:
        True if extension is enabled, False on error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
            conn.commit()
            logger.info("TimescaleDB extension enabled")
            return True
    except Exception as e:
        logger.error(f"Error enabling TimescaleDB extension: {e}")
        return False


def create_stock_table(schema_name: str = 'trading') -> bool:
    """
    Create the stock dimension table.
    
    Args:
        schema_name: Schema name where table will be created
    
    Returns:
        True if table was created, False on error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.stock (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL UNIQUE,
                    company_name TEXT NOT NULL
                );
            """)
            
            # Create index on id for fast lookups
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_stock_id 
                ON {schema_name}.stock (id);
            """)
            
            conn.commit()
            logger.info(f"Stock table created in schema '{schema_name}'")
            return True
    except Exception as e:
        logger.error(f"Error creating stock table: {e}")
        return False


def create_bars_table(schema_name: str = 'trading') -> bool:
    """
    Create the bars table for OHLCV data at minute scale.
    
    Args:
        schema_name: Schema name where table will be created
    
    Returns:
        True if table was created, False on error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create table with foreign key to stock
            # Matches init.sql: stock_id first, no trade_count, no created_at
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.bars (
                    stock_id INTEGER NOT NULL,
                    time TIMESTAMPTZ NOT NULL,
                    open NUMERIC(18, 4) NOT NULL,
                    high NUMERIC(18, 4) NOT NULL,
                    low NUMERIC(18, 4) NOT NULL,
                    close NUMERIC(18, 4) NOT NULL,
                    volume BIGINT NOT NULL,
                    vwap NUMERIC(18, 4),
                    PRIMARY KEY (time, stock_id),
                    FOREIGN KEY (stock_id) REFERENCES {schema_name}.stock(id) ON DELETE CASCADE
                );
            """)
            
            # Create indexes
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_bars_stock_id 
                ON {schema_name}.bars (stock_id);
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_bars_time_stock_id 
                ON {schema_name}.bars (time DESC, stock_id);
            """)
            
            conn.commit()
            logger.info(f"Bars table created in schema '{schema_name}'")
            return True
    except Exception as e:
        logger.error(f"Error creating bars table: {e}")
        return False


def create_quotes_table(schema_name: str = 'trading') -> bool:
    """
    Create the quotes table for bid/ask data.
    Schema matches Alpaca API response: ap (ask_price), as (ask_size), ax (ask_exchange),
    bp (bid_price), bs (bid_size), bx (bid_exchange), c (conditions), t (time), z (tape)
    
    Args:
        schema_name: Schema name where table will be created
    
    Returns:
        True if table was created, False on error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.quotes (
                    id SERIAL,
                    stock_id INTEGER NOT NULL,
                    time TIMESTAMPTZ NOT NULL,
                    bid_price NUMERIC(18, 4) NOT NULL,
                    bid_size INTEGER NOT NULL,
                    bid_exchange VARCHAR(1),
                    ask_price NUMERIC(18, 4) NOT NULL,
                    ask_size INTEGER NOT NULL,
                    ask_exchange VARCHAR(1),
                    conditions TEXT[],
                    tape VARCHAR(1),
                    PRIMARY KEY (time, stock_id, id),
                    FOREIGN KEY (stock_id) REFERENCES {schema_name}.stock(id) ON DELETE CASCADE,
                    UNIQUE (time, stock_id, bid_price, bid_size, ask_price, ask_size, bid_exchange, ask_exchange, tape)
                );
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_quotes_stock_id 
                ON {schema_name}.quotes (stock_id);
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_quotes_time_stock_id 
                ON {schema_name}.quotes (time DESC, stock_id);
            """)
            
            conn.commit()
            logger.info(f"Quotes table created in schema '{schema_name}'")
            return True
    except Exception as e:
        logger.error(f"Error creating quotes table: {e}")
        return False


def create_trades_table(schema_name: str = 'trading') -> bool:
    """
    Create the trades table for individual trade data.
    
    Args:
        schema_name: Schema name where table will be created
    
    Returns:
        True if table was created, False on error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.trades (
                    stock_id INTEGER NOT NULL,
                    trade_id INTEGER NOT NULL,
                    time TIMESTAMPTZ NOT NULL,
                    price NUMERIC(18, 4) NOT NULL,
                    size INTEGER NOT NULL,
                    conditions TEXT[],
                    exchange VARCHAR(1),
                    tape VARCHAR(1),
                    PRIMARY KEY (time, stock_id, trade_id),
                    FOREIGN KEY (stock_id) REFERENCES {schema_name}.stock(id) ON DELETE CASCADE
                );
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_trades_stock_id 
                ON {schema_name}.trades (stock_id);
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_trades_time_stock_id 
                ON {schema_name}.trades (time DESC, stock_id);
            """)
            
            conn.commit()
            logger.info(f"Trades table created in schema '{schema_name}'")
            return True
    except Exception as e:
        logger.error(f"Error creating trades table: {e}")
        return False


def create_hypertable(table_name: str, time_column: str = 'time', 
                     schema_name: str = 'trading',
                     chunk_time_interval: str = None) -> bool:
    """
    Convert a regular table to a TimescaleDB hypertable.
    
    Args:
        table_name: Name of the table to convert
        time_column: Name of the time column
        schema_name: Schema name
        chunk_time_interval: Time interval for chunking (e.g., "INTERVAL '1 day'")
                         If None, uses default based on table name
    
    Returns:
        True if hypertable was created, False on error
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if hypertable already exists
            cursor.execute(f"""
                SELECT COUNT(*) FROM timescaledb_information.hypertables 
                WHERE hypertable_schema = '{schema_name}' 
                AND hypertable_name = '{table_name}';
            """)
            
            if cursor.fetchone()[0] > 0:
                logger.info(f"Hypertable '{schema_name}.{table_name}' already exists")
                return True
            
            # Set default chunk interval if not provided
            if chunk_time_interval is None:
                # Bars table uses 6 hours for minute-scale data
                if table_name == 'bars':
                    chunk_time_interval = "INTERVAL '6 hours'"
                else:
                    chunk_time_interval = "INTERVAL '1 day'"
            
            # Create hypertable
            cursor.execute(f"""
                SELECT create_hypertable(
                    '{schema_name}.{table_name}',
                    '{time_column}',
                    chunk_time_interval => {chunk_time_interval},
                    if_not_exists => TRUE
                );
            """)
            
            conn.commit()
            logger.info(f"Hypertable created for '{schema_name}.{table_name}'")
            return True
    except Exception as e:
        logger.error(f"Error creating hypertable for '{table_name}': {e}")
        return False


def initialize_database(schema_name: str = 'trading') -> bool:
    """
    Initialize the entire database schema.
    Creates schema, enables extension, creates tables, and converts to hypertables.
    
    Args:
        schema_name: Name of the schema to create
    
    Returns:
        True if initialization was successful, False otherwise
    """
    logger.info("Initializing database schema...")
    
    steps = [
        ("Creating schema", lambda: create_schema(schema_name)),
        ("Enabling TimescaleDB extension", enable_timescaledb_extension),
        ("Creating stock dimension table", lambda: create_stock_table(schema_name)),
        ("Creating bars table", lambda: create_bars_table(schema_name)),
        ("Creating quotes table", lambda: create_quotes_table(schema_name)),
        ("Creating trades table", lambda: create_trades_table(schema_name)),
        ("Creating hypertable for bars", lambda: create_hypertable('bars', 'time', schema_name)),
        ("Creating hypertable for quotes", lambda: create_hypertable('quotes', 'time', schema_name)),
        ("Creating hypertable for trades", lambda: create_hypertable('trades', 'time', schema_name)),
    ]
    
    for step_name, step_func in steps:
        logger.info(f"Step: {step_name}")
        if not step_func():
            logger.error(f"Failed at step: {step_name}")
            return False
    
    logger.info("Database initialization completed successfully!")
    return True


def verify_schema(schema_name: str = 'trading') -> Tuple[bool, List[str]]:
    """
    Verify that the database schema is properly set up.
    
    Args:
        schema_name: Name of the schema to verify
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if schema exists
            cursor.execute(f"""
                SELECT 1 FROM information_schema.schemata 
                WHERE schema_name = '{schema_name}';
            """)
            if not cursor.fetchone():
                issues.append(f"Schema '{schema_name}' does not exist")
            
            # Check if TimescaleDB extension is enabled
            cursor.execute("""
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb';
            """)
            if not cursor.fetchone():
                issues.append("TimescaleDB extension is not enabled")
            
            # Check if tables exist
            tables = ['stock', 'bars', 'quotes', 'trades']
            for table in tables:
                cursor.execute(f"""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = '{schema_name}' AND table_name = '{table}';
                """)
                if not cursor.fetchone():
                    issues.append(f"Table '{schema_name}.{table}' does not exist")
            
            # Check if hypertables exist (stock is not a hypertable, only fact tables)
            hypertables = ['bars', 'quotes', 'trades']
            for table in hypertables:
                cursor.execute(f"""
                    SELECT 1 FROM timescaledb_information.hypertables 
                    WHERE hypertable_schema = '{schema_name}' 
                    AND hypertable_name = '{table}';
                """)
                if not cursor.fetchone():
                    issues.append(f"Hypertable '{schema_name}.{table}' does not exist")
            
    except Exception as e:
        issues.append(f"Error during verification: {e}")
    
    is_valid = len(issues) == 0
    return is_valid, issues

