# Docker & Database Setup - Implementation Complete

## Overview
This document summarizes what has been implemented for the Docker and TimescaleDB setup.

## What Was Created

### 1. Docker Configuration (`docker/`)
- **`docker-compose.yml`**: Docker Compose configuration for TimescaleDB
  - Uses `timescale/timescaledb:latest-pg17` image
  - Maps port 5433 (host) to 5432 (container)
  - Creates persistent volume for data
  - Includes health checks
  - Automatically runs `init.sql` on first startup

- **`init.sql`**: Database initialization script
  - Enables TimescaleDB extension
  - Creates `trading` schema
  - Creates three tables: `bars`, `quotes`, `trades`
  - Converts tables to hypertables (time-series optimization)
  - Creates indexes for performance

### 2. Shell Scripts (`scripts/`)
All scripts are executable and include error handling:

- **`setup_docker.sh`**: Main orchestrator script
  - Checks Docker installation
  - Creates/starts container if needed
  - Waits for database to be ready
  - Verifies database setup

- **`start_container.sh`**: Starts existing container
  - Checks if container exists
  - Starts container
  - Waits for database readiness

- **`stop_container.sh`**: Stops container gracefully

- **`check_container.sh`**: Checks container status
  - Returns exit codes: 0=running, 2=stopped, 3=doesn't exist

- **`init_database.sh`**: Initializes database schema
  - Runs SQL initialization script
  - Can be used to re-run initialization

### 3. Python Modules (`src/data/`)

- **`db_connection.py`**: Database connection management
  - Connection pooling with `psycopg2`
  - Retry logic with exponential backoff
  - Context manager for automatic connection handling
  - Health check functions
  - Environment variable configuration

- **`db_schema.py`**: Database schema management
  - Schema creation
  - Table creation (bars, quotes, trades)
  - Hypertable creation
  - Schema verification
  - Full database initialization function

- **`__init__.py`**: Module exports for easy imports

### 4. Tests (`tests/`)

- **`test_db_connection.py`**: Unit tests for connection module
  - Tests connection pooling
  - Tests retry logic
  - Tests context manager
  - Tests error handling

- **`test_db_schema.py`**: Unit tests for schema module
  - Tests schema creation
  - Tests table creation
  - Tests hypertable creation
  - Tests initialization workflow

- **`test_scripts.py`**: Integration tests for shell scripts
  - Verifies scripts exist and are executable
  - Validates bash syntax
  - Checks Docker Compose configuration
  - Verifies SQL initialization script

- **`run_tests.sh`**: Test runner script

### 5. Configuration

- **`.env.example`**: Environment variable template
  - TimescaleDB connection settings
  - Alpaca API configuration
  - (Note: You'll need to create `.env` file from this template)

## How to Use

### Initial Setup

1. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

2. **Make scripts executable** (if not already):
   ```bash
   chmod +x scripts/*.sh
   chmod +x tests/run_tests.sh
   ```

3. **Run the setup script**:
   ```bash
   ./scripts/setup_docker.sh
   ```

   This will:
   - Check Docker installation
   - Create and start the TimescaleDB container
   - Wait for database to be ready
   - Initialize the database schema

### Daily Usage

**Start the container** (if stopped):
```bash
./scripts/start_container.sh
```

**Stop the container**:
```bash
./scripts/stop_container.sh
```

**Check container status**:
```bash
./scripts/check_container.sh
```

**Re-initialize database** (if needed):
```bash
./scripts/init_database.sh
```

### Using Python Modules

```python
from src.data import get_db_connection, initialize_database, verify_schema

# Initialize database (one-time setup)
initialize_database('trading')

# Verify schema
is_valid, issues = verify_schema('trading')
if not is_valid:
    print(f"Issues found: {issues}")

# Use database connection
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trading.bars LIMIT 10")
    results = cursor.fetchall()
```

### Running Tests

**Run all tests**:
```bash
./tests/run_tests.sh
```

**Run specific test file**:
```bash
python -m pytest tests/test_db_connection.py -v
python -m unittest tests.test_db_schema
```

## Database Schema

### Tables Created

1. **`trading.bars`**: OHLCV (Open, High, Low, Close, Volume) data
   - Primary key: (time, symbol)
   - Columns: time, symbol, open, high, low, close, volume, trade_count, vwap

2. **`trading.quotes`**: Bid/Ask quote data
   - Primary key: (time, symbol)
   - Columns: time, symbol, bid_price, bid_size, ask_price, ask_size

3. **`trading.trades`**: Individual trade data
   - Primary key: (time, symbol, price, size)
   - Columns: time, symbol, price, size, conditions, tape

All tables are converted to TimescaleDB hypertables with daily chunking for optimal time-series performance.

## Connection Details

- **Host**: localhost
- **Port**: 5433 (host) → 5432 (container)
- **Database**: trading_db
- **User**: postgres
- **Password**: Set in `.env` file or docker-compose.yml

## Code Explanation

### Database Connection Module (`db_connection.py`)

**Connection Pooling**: Uses `psycopg2.ThreadedConnectionPool` to manage multiple database connections efficiently. This avoids creating a new connection for every database operation.

**Retry Logic**: The `get_connection()` function implements exponential backoff retry logic. If a connection fails, it waits progressively longer before retrying (1s, 2s, 3s, etc.).

**Context Manager**: The `get_db_connection()` context manager automatically handles:
- Connection acquisition
- Error handling with rollback
- Connection return to pool
- This ensures connections are always properly cleaned up

**Environment Variables**: Connection settings are loaded from environment variables using `python-dotenv`, making it easy to configure for different environments.

### Database Schema Module (`db_schema.py`)

**Modular Design**: Each table has its own creation function, making it easy to create tables individually or all at once.

**Hypertable Creation**: The `create_hypertable()` function:
1. Checks if hypertable already exists (to avoid errors)
2. Calls TimescaleDB's `create_hypertable()` function
3. Partitions data by time (daily chunks by default)

**Initialization Workflow**: The `initialize_database()` function runs all setup steps in order:
1. Create schema
2. Enable TimescaleDB extension
3. Create all tables
4. Convert tables to hypertables

**Verification**: The `verify_schema()` function checks:
- Schema existence
- Extension enabled
- All tables exist
- All hypertables exist
- Returns a list of any issues found

### Shell Scripts

**Error Handling**: All scripts use `set -e` to exit on any error, preventing partial execution states.

**Status Checking**: Scripts check Docker status, container existence, and database readiness before proceeding.

**Wait Logic**: Scripts include wait loops that check database readiness using `pg_isready`, with configurable timeouts.

**Path Resolution**: Scripts use `$(cd ... && pwd)` to resolve absolute paths, making them work from any directory.

## Next Steps

The Docker and database setup is complete! Next, you can:

1. **Create Alpaca ingestion script** (`src/data/alpaca_ingestion.py`)
   - Use the `get_db_connection()` function to connect
   - Fetch data from Alpaca API
   - Insert data into the tables

2. **Test the setup**:
   ```bash
   # Start container
   ./scripts/start_container.sh
   
   # Test Python connection
   python -c "from src.data import test_connection; test_connection()"
   
   # Verify schema
   python -c "from src.data import verify_schema; print(verify_schema())"
   ```

3. **Add data ingestion**: Once the ingestion script is created, you can start collecting data from Alpaca API.

## Troubleshooting

**Container won't start**:
- Check Docker is running: `docker info`
- Check logs: `docker logs algo_trading_timescaledb`
- Check port conflicts: `netstat -an | grep 5433`

**Database connection fails**:
- Verify container is running: `./scripts/check_container.sh`
- Check environment variables in `.env`
- Test connection: `python -c "from src.data import test_connection; test_connection()"`

**Schema initialization fails**:
- Check container logs: `docker logs algo_trading_timescaledb`
- Manually run init: `./scripts/init_database.sh`
- Verify SQL syntax: Check `docker/init.sql`

