"""
Tests for database connection module.
"""

import unittest
import os
from unittest.mock import patch, MagicMock
import psycopg2

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.data.db_connection import (
    get_connection_pool,
    get_connection,
    return_connection,
    get_db_connection,
    test_connection,
    wait_for_database,
    close_all_connections,
    DB_CONFIG,
)


class TestDBConnection(unittest.TestCase):
    """Test cases for database connection functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset connection pool before each test
        import src.data.db_connection as db_conn_module
        db_conn_module._connection_pool = None
    
    def tearDown(self):
        """Clean up after tests."""
        close_all_connections()
    
    def test_db_config_defaults(self):
        """Test that DB_CONFIG has expected default values."""
        self.assertIn('host', DB_CONFIG)
        self.assertIn('port', DB_CONFIG)
        self.assertIn('database', DB_CONFIG)
        self.assertIn('user', DB_CONFIG)
        self.assertIn('password', DB_CONFIG)
        self.assertEqual(DB_CONFIG['host'], 'localhost')
        self.assertEqual(DB_CONFIG['port'], 5433)
        self.assertEqual(DB_CONFIG['database'], 'trading_db')
    
    @patch('src.data.db_connection.pool.ThreadedConnectionPool')
    def test_get_connection_pool_creation(self, mock_pool_class):
        """Test connection pool creation."""
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        
        pool = get_connection_pool()
        
        self.assertIsNotNone(pool)
        mock_pool_class.assert_called_once()
    
    @patch('src.data.db_connection.get_connection_pool')
    def test_get_connection_success(self, mock_get_pool):
        """Test successful connection retrieval."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_get_pool.return_value = mock_pool
        
        conn = get_connection()
        
        self.assertIsNotNone(conn)
        mock_pool.getconn.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT 1")
    
    @patch('src.data.db_connection.get_connection_pool')
    def test_get_connection_retry(self, mock_get_pool):
        """Test connection retry logic on failure."""
        mock_pool = MagicMock()
        mock_pool.getconn.side_effect = [
            psycopg2.Error("Connection failed"),
            MagicMock()  # Success on second attempt
        ]
        mock_get_pool.return_value = mock_pool
        
        # Mock cursor for successful connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.getconn.side_effect = [
            psycopg2.Error("Connection failed"),
            mock_conn
        ]
        
        with patch('time.sleep'):  # Speed up test by mocking sleep
            conn = get_connection(max_retries=3)
        
        self.assertIsNotNone(conn)
        self.assertEqual(mock_pool.getconn.call_count, 2)
    
    @patch('src.data.db_connection.get_connection_pool')
    def test_return_connection(self, mock_get_pool):
        """Test returning connection to pool."""
        mock_pool = MagicMock()
        mock_get_pool.return_value = mock_pool
        mock_conn = MagicMock()
        
        return_connection(mock_conn)
        
        mock_pool.putconn.assert_called_once_with(mock_conn)
    
    @patch('src.data.db_connection.get_connection')
    def test_get_db_connection_context_manager_success(self, mock_get_conn):
        """Test context manager for successful connection."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        with get_db_connection() as conn:
            self.assertEqual(conn, mock_conn)
        
        mock_get_conn.assert_called_once()
    
    @patch('src.data.db_connection.get_connection')
    @patch('src.data.db_connection.return_connection')
    def test_get_db_connection_context_manager_error(self, mock_return_conn, mock_get_conn):
        """Test context manager handles errors correctly."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        # Simulate an error
        mock_conn.cursor.side_effect = psycopg2.Error("Test error")
        
        with self.assertRaises(psycopg2.Error):
            with get_db_connection() as conn:
                conn.cursor()
        
        mock_conn.rollback.assert_called_once()
        mock_return_conn.assert_called_once_with(mock_conn)
    
    @patch('src.data.db_connection.get_db_connection')
    def test_test_connection_success(self, mock_get_db_conn):
        """Test successful connection test."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('PostgreSQL 17.0',)
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = test_connection()
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called_once_with("SELECT version();")
    
    @patch('src.data.db_connection.get_db_connection')
    def test_test_connection_failure(self, mock_get_db_conn):
        """Test connection test failure."""
        mock_get_db_conn.side_effect = psycopg2.Error("Connection failed")
        
        result = test_connection()
        
        self.assertFalse(result)
    
    @patch('src.data.db_connection.test_connection')
    @patch('time.sleep')
    def test_wait_for_database_success(self, mock_sleep, mock_test_conn):
        """Test waiting for database when it becomes available."""
        mock_test_conn.side_effect = [False, False, True]  # Available on 3rd attempt
        
        result = wait_for_database(max_attempts=5, delay=0.1)
        
        self.assertTrue(result)
        self.assertEqual(mock_test_conn.call_count, 3)
    
    @patch('src.data.db_connection.test_connection')
    @patch('time.sleep')
    def test_wait_for_database_timeout(self, mock_sleep, mock_test_conn):
        """Test waiting for database when it times out."""
        mock_test_conn.return_value = False  # Never becomes available
        
        result = wait_for_database(max_attempts=3, delay=0.1)
        
        self.assertFalse(result)
        self.assertEqual(mock_test_conn.call_count, 3)
    
    @patch('src.data.db_connection.pool.ThreadedConnectionPool')
    def test_close_all_connections(self, mock_pool_class):
        """Test closing all connections."""
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        
        # Create a pool first
        get_connection_pool()
        
        close_all_connections()
        
        mock_pool.closeall.assert_called_once()


if __name__ == '__main__':
    unittest.main()

