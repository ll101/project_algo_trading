# Docker & TimescaleDB Setup Plan

## Overview
This plan outlines the architecture and implementation approach for setting up a TimescaleDB container and Alpaca API data ingestion pipeline.

## Architecture Components

### 1. Docker Infrastructure
- **TimescaleDB Container**: Use official `timescale/timescaledb` image
- **Container Management**: Scripts to handle container lifecycle
- **Data Persistence**: Docker volumes for database data
- **Network**: Docker network for container communication (if needed)

### 2. Database Setup
- **Initialization Scripts**: SQL scripts for database and schema creation
- **TimescaleDB Extension**: Enable hypertables for time-series data
- **Table Schema**: Design tables for Alpaca market data (bars, quotes, trades)

### 3. Data Ingestion
- **Alpaca API Client**: Use existing `alpaca-py` library
- **Connection Manager**: Database connection handling with retry logic
- **Data Pipeline**: Fetch data from Alpaca and insert into TimescaleDB
- **Error Handling**: Robust error handling and logging

## File Structure

```
project_algo_trading/
├── docker/
│   ├── docker-compose.yml          # Docker Compose for TimescaleDB
│   └── init.sql                    # Database initialization SQL
├── scripts/
│   ├── setup_docker.sh             # Main setup script (orchestrates everything)
│   ├── start_container.sh          # Start TimescaleDB container
│   ├── stop_container.sh           # Stop TimescaleDB container
│   ├── init_database.sh            # Initialize database and schema
│   └── check_container.sh          # Check if container exists/running
├── src/
│   └── data/
│       ├── db_connection.py        # Database connection utilities
│       ├── db_schema.py            # Database schema definitions
│       ├── alpaca_ingestion.py     # Main Alpaca data ingestion script
│       └── models.py               # Data models/schemas
├── .env.example                    # Environment variables template
└── requirements.txt                # Already has alpaca-py, psycopg2-binary
```

## Implementation Steps

### Step 1: Docker Configuration
**Files to create:**
- `docker/docker-compose.yml`: Define TimescaleDB service
- `docker/init.sql`: Initial database setup SQL

**Key considerations:**
- Use official `timescale/timescaledb:latest-pg16` or specific version
- Map port 5432 to host (e.g., 5433 to avoid conflicts)
- Create named volume for data persistence
- Set environment variables for database credentials
- Use health checks to ensure DB is ready

### Step 2: Container Management Scripts
**Files to create:**
- `scripts/setup_docker.sh`: Main orchestrator script
  - Check if Docker is installed
  - Check if container exists
  - Build/start container if needed
  - Wait for DB to be ready
  - Run database initialization
  - Start data ingestion

- `scripts/start_container.sh`: Start existing container
- `scripts/stop_container.sh`: Stop container
- `scripts/check_container.sh`: Check container status
- `scripts/init_database.sh`: Run database initialization

**Script logic:**
```bash
# Pseudo-code for setup_docker.sh
1. Check Docker installation
2. Check if container exists (docker ps -a)
3. If not exists:
   - docker-compose up -d
4. If exists but stopped:
   - docker start <container_name>
5. Wait for DB health check
6. Run init_database.sh
7. Start Python ingestion script
```

### Step 3: Database Initialization
**Files to create:**
- `docker/init.sql`: SQL script for:
  - Create database if not exists
  - Create user/role if needed
  - Enable TimescaleDB extension
  - Create initial tables (bars, quotes, trades, etc.)
  - Create hypertables for time-series data

**Alternative approach:**
- Use Python script (`src/data/db_schema.py`) to initialize schema
- More flexible for complex logic
- Can use SQLAlchemy or raw SQL

### Step 4: Database Connection Module
**Files to create:**
- `src/data/db_connection.py`:
  - Connection pool management
  - Retry logic
  - Connection health checks
  - Environment variable configuration

### Step 5: Data Ingestion Script
**Files to create:**
- `src/data/alpaca_ingestion.py`:
  - Initialize Alpaca API client
  - Connect to TimescaleDB
  - Fetch data from Alpaca (bars, quotes, trades)
  - Insert data into TimescaleDB
  - Handle errors and retries
  - Logging for monitoring

**Data types to ingest:**
- Historical bars (OHLCV)
- Real-time bars (if using websockets)
- Quotes
- Trades

## Environment Variables

Create `.env.example` with:
```env
# TimescaleDB Configuration
TIMESCALEDB_HOST=localhost
TIMESCALEDB_PORT=5433
TIMESCALEDB_DB=trading_db
TIMESCALEDB_USER=postgres
TIMESCALEDB_PASSWORD=your_password_here

# Alpaca API Configuration
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # or https://api.alpaca.markets
```

## Database Schema Design

### Tables to create:
1. **bars** (OHLCV data)
   - timestamp (primary time dimension)
   - symbol
   - open, high, low, close
   - volume
   - trade_count (if available)

2. **quotes** (bid/ask data)
   - timestamp
   - symbol
   - bid_price, bid_size
   - ask_price, ask_size

3. **trades** (trade data)
   - timestamp
   - symbol
   - price
   - size

**TimescaleDB Hypertables:**
- Convert regular tables to hypertables for time-series optimization
- Partition by time (e.g., daily or weekly chunks)

## Execution Flow

1. **Initial Setup** (one-time):
   ```bash
   ./scripts/setup_docker.sh
   ```

2. **Daily Usage**:
   ```bash
   # Start container if stopped
   ./scripts/start_container.sh
   
   # Run ingestion
   python src/data/alpaca_ingestion.py
   ```

3. **Stop Container**:
   ```bash
   ./scripts/stop_container.sh
   ```

## Error Handling & Best Practices

1. **Container Management**:
   - Check if Docker is running
   - Handle container already exists scenarios
   - Graceful shutdown handling

2. **Database Connection**:
   - Connection pooling
   - Retry logic with exponential backoff
   - Connection timeout handling

3. **Data Ingestion**:
   - Handle API rate limits
   - Duplicate data prevention
   - Batch inserts for performance
   - Transaction management

4. **Logging**:
   - Structured logging
   - Log levels (INFO, WARNING, ERROR)
   - Log rotation

## Testing Strategy

1. **Unit Tests**:
   - Database connection tests
   - Schema creation tests
   - Data insertion tests

2. **Integration Tests**:
   - End-to-end container setup
   - Alpaca API connection
   - Data ingestion pipeline

3. **Manual Testing**:
   - Verify container starts correctly
   - Verify database is accessible
   - Verify data ingestion works

## Next Steps

1. Create Docker Compose configuration
2. Create container management scripts
3. Create database initialization SQL/Python
4. Create database connection module
5. Create Alpaca ingestion script
6. Create environment variable template
7. Test the complete pipeline
8. Add error handling and logging
9. Document usage instructions

## Dependencies to Add

Consider adding to `requirements.txt`:
- `python-dotenv` (for .env file handling)
- `sqlalchemy` (optional, for ORM)
- `timescaledb` (Python client utilities, optional)

