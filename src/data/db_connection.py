"""
Database Connection Module
Handles connection to TimescaleDB with retry logic and connection pooling.
"""

import os
import time
import logging
from typing import Optional
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('TIMESCALEDB_HOST', 'localhost'),
    'port': int(os.getenv('TIMESCALEDB_PORT', '5433')),
    'database': os.getenv('TIMESCALEDB_DB', 'trading_db'),
    'user': os.getenv('TIMESCALEDB_USER', 'postgres'),
    'password': os.getenv('TIMESCALEDB_PASSWORD', 'postgres'),
}

# Connection pool (initialized on first use)
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def get_connection_pool(min_conn: int = 1, max_conn: int = 10) -> pool.ThreadedConnectionPool:
    """
    Get or create a connection pool.
    
    Args:
        min_conn: Minimum number of connections in the pool
        max_conn: Maximum number of connections in the pool
    
    Returns:
        ThreadedConnectionPool instance
    """
    global _connection_pool
    
    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                min_conn, max_conn,
                **DB_CONFIG
            )
            logger.info("Connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise
    
    return _connection_pool


def get_connection(max_retries: int = 3, retry_delay: float = 1.0):
    """
    Get a database connection from the pool with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        psycopg2 connection object
    
    Raises:
        psycopg2.Error: If connection fails after all retries
    """
    pool = get_connection_pool()
    
    for attempt in range(max_retries):
        try:
            conn = pool.getconn()
            if conn:
                # Test the connection
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                return conn
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                logger.error("Failed to get connection after all retries")
                raise
    
    raise psycopg2.Error("Failed to get database connection")


def return_connection(conn):
    """
    Return a connection to the pool.
    
    Args:
        conn: psycopg2 connection object to return
    """
    pool = get_connection_pool()
    try:
        pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error returning connection to pool: {e}")


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Automatically handles connection acquisition and return.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trading.bars")
            results = cursor.fetchall()
    """
    conn = None
    try:
        conn = get_connection()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def test_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            logger.info(f"Database connection successful. PostgreSQL version: {version[0]}")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def wait_for_database(max_attempts: int = 30, delay: float = 1.0) -> bool:
    """
    Wait for database to become available.
    Useful when starting containers and need to wait for DB to be ready.
    
    Args:
        max_attempts: Maximum number of connection attempts
        delay: Delay between attempts in seconds
    
    Returns:
        True if database becomes available, False otherwise
    """
    logger.info("Waiting for database to become available...")
    
    for attempt in range(max_attempts):
        if test_connection():
            logger.info("Database is ready!")
            return True
        logger.debug(f"Attempt {attempt + 1}/{max_attempts} - database not ready yet")
        time.sleep(delay)
    
    logger.error("Database did not become available in time")
    return False


def close_all_connections():
    """
    Close all connections in the pool.
    Call this when shutting down the application.
    """
    global _connection_pool
    
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("All database connections closed")

