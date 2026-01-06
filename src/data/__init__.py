"""
Data module for database operations and data ingestion.
"""

from .db_connection import (
    get_db_connection,
    test_connection,
    wait_for_database,
    close_all_connections,
)
from .db_schema import (
    initialize_database,
    verify_schema,
    create_schema,
    enable_timescaledb_extension,
    create_stock_table,
    create_bars_table,
    create_quotes_table,
    create_trades_table,
)
from .db_ingestion import (
    insert_bars_idempotent,
    insert_quotes_idempotent,
    insert_trades_idempotent,
    get_or_create_stock,
    fetch_nasdaq100_tickers,
    insert_nasdaq100_stocks,
)

__all__ = [
    'get_db_connection',
    'test_connection',
    'wait_for_database',
    'close_all_connections',
    'initialize_database',
    'verify_schema',
    'create_schema',
    'enable_timescaledb_extension',
    'create_stock_table',
    'create_bars_table',
    'create_quotes_table',
    'create_trades_table',
    'insert_bars_idempotent',
    'insert_quotes_idempotent',
    'insert_trades_idempotent',
    'get_or_create_stock',
    'fetch_nasdaq100_tickers',
    'insert_nasdaq100_stocks',
]

