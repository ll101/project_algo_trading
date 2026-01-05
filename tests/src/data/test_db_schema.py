"""
Tests for database schema module.
"""

import unittest
import os
from unittest.mock import patch, MagicMock

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.data.db_schema import (
    create_schema,
    enable_timescaledb_extension,
    create_bars_table,
    create_quotes_table,
    create_trades_table,
    create_hypertable,
    initialize_database,
    verify_schema,
)


class TestDBSchema(unittest.TestCase):
    """Test cases for database schema functionality."""
    
    @patch('src.data.db_schema.get_db_connection')
    def test_create_schema_success(self, mock_get_db_conn):
        """Test successful schema creation."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = create_schema('test_schema')
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
    
    @patch('src.data.db_schema.get_db_connection')
    def test_create_schema_error(self, mock_get_db_conn):
        """Test schema creation with error."""
        mock_get_db_conn.side_effect = Exception("Database error")
        
        result = create_schema('test_schema')
        
        self.assertFalse(result)
    
    @patch('src.data.db_schema.get_db_connection')
    def test_enable_timescaledb_extension_success(self, mock_get_db_conn):
        """Test enabling TimescaleDB extension."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = enable_timescaledb_extension()
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called_with("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        mock_conn.commit.assert_called_once()
    
    @patch('src.data.db_schema.get_db_connection')
    def test_create_bars_table_success(self, mock_get_db_conn):
        """Test creating bars table."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = create_bars_table('trading')
        
        self.assertTrue(result)
        # Should execute CREATE TABLE and CREATE INDEX statements
        self.assertGreater(mock_cursor.execute.call_count, 1)
        mock_conn.commit.assert_called_once()
    
    @patch('src.data.db_schema.get_db_connection')
    def test_create_quotes_table_success(self, mock_get_db_conn):
        """Test creating quotes table."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = create_quotes_table('trading')
        
        self.assertTrue(result)
        self.assertGreater(mock_cursor.execute.call_count, 1)
        mock_conn.commit.assert_called_once()
    
    @patch('src.data.db_schema.get_db_connection')
    def test_create_trades_table_success(self, mock_get_db_conn):
        """Test creating trades table."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = create_trades_table('trading')
        
        self.assertTrue(result)
        self.assertGreater(mock_cursor.execute.call_count, 1)
        mock_conn.commit.assert_called_once()
    
    @patch('src.data.db_schema.get_db_connection')
    def test_create_hypertable_new(self, mock_get_db_conn):
        """Test creating a new hypertable."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First call: check if hypertable exists (returns 0)
        # Second call: create hypertable
        mock_cursor.fetchone.side_effect = [(0,), None]  # Doesn't exist, then create
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = create_hypertable('bars', 'time', 'trading')
        
        self.assertTrue(result)
        self.assertGreater(mock_cursor.execute.call_count, 1)
        mock_conn.commit.assert_called_once()
    
    @patch('src.data.db_schema.get_db_connection')
    def test_create_hypertable_exists(self, mock_get_db_conn):
        """Test creating hypertable when it already exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # Already exists
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        result = create_hypertable('bars', 'time', 'trading')
        
        self.assertTrue(result)
        # Should only check, not create
        mock_cursor.execute.assert_called_once()
    
    @patch('src.data.db_schema.create_hypertable')
    @patch('src.data.db_schema.create_trades_table')
    @patch('src.data.db_schema.create_quotes_table')
    @patch('src.data.db_schema.create_bars_table')
    @patch('src.data.db_schema.enable_timescaledb_extension')
    @patch('src.data.db_schema.create_schema')
    def test_initialize_database_success(self, mock_create_schema, mock_enable_ext,
                                         mock_create_bars, mock_create_quotes,
                                         mock_create_trades, mock_create_hypertable):
        """Test full database initialization."""
        # All functions return True (success)
        mock_create_schema.return_value = True
        mock_enable_ext.return_value = True
        mock_create_bars.return_value = True
        mock_create_quotes.return_value = True
        mock_create_trades.return_value = True
        mock_create_hypertable.return_value = True
        
        result = initialize_database('trading')
        
        self.assertTrue(result)
        mock_create_schema.assert_called_once_with('trading')
        mock_enable_ext.assert_called_once()
        mock_create_bars.assert_called_once()
        mock_create_quotes.assert_called_once()
        mock_create_trades.assert_called_once()
        # Should create 3 hypertables
        self.assertEqual(mock_create_hypertable.call_count, 3)
    
    @patch('src.data.db_schema.create_schema')
    def test_initialize_database_failure(self, mock_create_schema):
        """Test database initialization failure."""
        mock_create_schema.return_value = False  # First step fails
        
        result = initialize_database('trading')
        
        self.assertFalse(result)
    
    @patch('src.data.db_schema.get_db_connection')
    def test_verify_schema_success(self, mock_get_db_conn):
        """Test schema verification when everything exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # All checks return True (exists)
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        is_valid, issues = verify_schema('trading')
        
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
    
    @patch('src.data.db_schema.get_db_connection')
    def test_verify_schema_with_issues(self, mock_get_db_conn):
        """Test schema verification when things are missing."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Schema doesn't exist, then extension doesn't exist, etc.
        mock_cursor.fetchone.return_value = None  # Nothing exists
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        
        is_valid, issues = verify_schema('trading')
        
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)
        # Should have issues for schema, extension, and tables
        self.assertIn('Schema', issues[0] or '')
    
    @patch('src.data.db_schema.get_db_connection')
    def test_verify_schema_error(self, mock_get_db_conn):
        """Test schema verification with database error."""
        mock_get_db_conn.side_effect = Exception("Connection error")
        
        is_valid, issues = verify_schema('trading')
        
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)
        self.assertIn('Error', issues[0])


if __name__ == '__main__':
    unittest.main()

