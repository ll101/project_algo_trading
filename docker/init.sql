-- TimescaleDB Initialization Script
-- This script runs automatically when the container is first created

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create schema for trading data (optional, keeps things organized)
CREATE SCHEMA IF NOT EXISTS trading;

-- Create stock dimension table (must be created before fact tables)
CREATE TABLE IF NOT EXISTS trading.stock (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL

);

-- Create index on symbol for fast lookups
CREATE INDEX IF NOT EXISTS idx_stock_id ON trading.stock (id);

-- Create bars table for OHLCV (Open, High, Low, Close, Volume) data at minute scale
CREATE TABLE IF NOT EXISTS trading.bars (
    stock_id INTEGER NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    open NUMERIC(18, 4) NOT NULL,
    high NUMERIC(18, 4) NOT NULL,
    low NUMERIC(18, 4) NOT NULL,
    close NUMERIC(18, 4) NOT NULL,
    volume BIGINT NOT NULL,
    vwap NUMERIC(18, 4),  -- Volume Weighted Average Price
    PRIMARY KEY (time, stock_id),
    FOREIGN KEY (stock_id) REFERENCES trading.stock(id) ON DELETE CASCADE
);

-- Create hypertable for bars (TimescaleDB optimization for time-series)
-- Using 6 hour chunks for minute-scale data
SELECT create_hypertable('trading.bars', 'time', 
    chunk_time_interval => INTERVAL '6 hours',
    if_not_exists => TRUE
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_bars_stock_id ON trading.bars (stock_id);
CREATE INDEX IF NOT EXISTS idx_bars_time_stock_id ON trading.bars (time DESC, stock_id);

-- Create quotes table for bid/ask data
-- Schema matches Alpaca API response: ap (ask_price), as (ask_size), ax (ask_exchange),
-- bp (bid_price), bs (bid_size), bx (bid_exchange), c (conditions), t (time), z (tape)
-- Uses serial id for uniqueness, but PRIMARY KEY includes time for TimescaleDB compatibility
-- UNIQUE constraint on idempotency fields ensures no duplicate ingestion
CREATE TABLE IF NOT EXISTS trading.quotes (
    id SERIAL,
    stock_id INTEGER NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    bid_price NUMERIC(18, 4) NOT NULL,
    bid_size INTEGER NOT NULL,
    bid_exchange VARCHAR(1),  -- Exchange identifier for bid (bx in API)
    ask_price NUMERIC(18, 4) NOT NULL,
    ask_size INTEGER NOT NULL,
    ask_exchange VARCHAR(1),  -- Exchange identifier for ask (ax in API)
    conditions TEXT[],  -- Array of quote conditions (c in API)
    tape VARCHAR(1),    -- Exchange tape identifier (z in API)
    PRIMARY KEY (time, stock_id, id),  -- Includes time for TimescaleDB partitioning
    FOREIGN KEY (stock_id) REFERENCES trading.stock(id) ON DELETE CASCADE,
    UNIQUE (time, stock_id, bid_price, bid_size, ask_price, ask_size, bid_exchange, ask_exchange, tape)
);

-- Create hypertable for quotes
SELECT create_hypertable('trading.quotes', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for quotes
CREATE INDEX IF NOT EXISTS idx_quotes_stock_id ON trading.quotes (stock_id);
CREATE INDEX IF NOT EXISTS idx_quotes_time_stock_id ON trading.quotes (time DESC, stock_id);

-- Create trades table for individual trade data
-- Schema matches Alpaca API response: c (conditions), i (trade_id), p (price), s (size),
-- t (time), x (exchange), z (tape)
-- Uses (time, stock_id, trade_id) as primary key - includes time for TimescaleDB partitioning
-- trade_id is unique per stock, and time ensures TimescaleDB compatibility
CREATE TABLE IF NOT EXISTS trading.trades (
    stock_id INTEGER NOT NULL,
    trade_id INTEGER NOT NULL,  -- Unique trade identifier from API (i in API)
    time TIMESTAMPTZ NOT NULL,
    price NUMERIC(18, 4) NOT NULL,
    size INTEGER NOT NULL,
    conditions TEXT[],  -- Array of trade conditions (c in API)
    exchange VARCHAR(1),  -- Exchange identifier (x in API)
    tape VARCHAR(1),    -- Exchange tape identifier (z in API)
    PRIMARY KEY (time, stock_id, trade_id),  -- Includes time for TimescaleDB partitioning
    FOREIGN KEY (stock_id) REFERENCES trading.stock(id) ON DELETE CASCADE
);

-- Create hypertable for trades
SELECT create_hypertable('trading.trades', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for trades
CREATE INDEX IF NOT EXISTS idx_trades_stock_id ON trading.trades (stock_id);
CREATE INDEX IF NOT EXISTS idx_trades_time_stock_id ON trading.trades (time DESC, stock_id);

-- Grant permissions (if using a different user)
-- GRANT ALL PRIVILEGES ON SCHEMA trading TO postgres;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trading TO postgres;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB initialization completed successfully';
    RAISE NOTICE 'Tables created: stock (dimension), bars, quotes, trades (fact tables)';
    RAISE NOTICE 'All fact tables have foreign keys to stock table';
END $$;

