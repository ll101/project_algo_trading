#!/bin/bash
# setup_docker.sh
# Main orchestrator script that sets up the TimescaleDB Docker container
# This script:
# 1. Checks if Docker is installed and running
# 2. Checks if container exists
# 3. Creates/starts container if needed
# 4. Waits for database to be ready
# 5. Initializes database schema

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"
CONTAINER_NAME="algo_trading_timescaledb"

echo "=========================================="
echo "TimescaleDB Docker Setup"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Determine docker-compose command (newer versions use 'docker compose', older use 'docker-compose')
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Check if docker-compose.yml exists
if [ ! -f "${DOCKER_DIR}/docker-compose.yml" ]; then
    echo "Error: docker-compose.yml not found at ${DOCKER_DIR}/docker-compose.yml"
    exit 1
fi

# Check container status
echo "Checking container status..."
CONTAINER_EXISTS=false
CONTAINER_RUNNING=false

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    CONTAINER_EXISTS=true
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        CONTAINER_RUNNING=true
    fi
fi

# Handle different scenarios
if [ "$CONTAINER_RUNNING" = true ]; then
    echo "Container '${CONTAINER_NAME}' is already running."
    echo "Skipping container creation."
elif [ "$CONTAINER_EXISTS" = true ]; then
    echo "Container '${CONTAINER_NAME}' exists but is stopped."
    echo "Starting container..."
    docker start "${CONTAINER_NAME}" > /dev/null 2>&1
    echo "Container started successfully."
else
    echo "Container '${CONTAINER_NAME}' does not exist."
    echo "Creating and starting container..."
    
    # Change to docker directory to run docker-compose
    cd "${DOCKER_DIR}"
    
    # Create and start the container
    ${DOCKER_COMPOSE_CMD} up -d
    
    echo "Container created and started successfully."
fi

# Wait for database to be ready
echo ""
echo "Waiting for database to be ready..."
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker exec "${CONTAINER_NAME}" pg_isready -U postgres -d trading_db > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
done
echo ""

if [ $attempt -eq $max_attempts ]; then
    echo "Warning: Database did not become ready in time."
    echo "You may need to check the container logs: docker logs ${CONTAINER_NAME}"
    exit 1
fi

# Verify database initialization
echo ""
echo "Verifying database setup..."
sleep 2  # Give it a moment for init.sql to complete

# Check if TimescaleDB extension is enabled
if docker exec "${CONTAINER_NAME}" psql -U postgres -d trading_db -tAc \
    "SELECT 1 FROM pg_extension WHERE extname='timescaledb'" | grep -q 1; then
    echo "✓ TimescaleDB extension is enabled"
else
    echo "⚠ TimescaleDB extension may not be enabled. This is normal if init.sql hasn't run yet."
fi

# Check if trading schema exists
if docker exec "${CONTAINER_NAME}" psql -U postgres -d trading_db -tAc \
    "SELECT 1 FROM information_schema.schemata WHERE schema_name='trading'" | grep -q 1; then
    echo "✓ Trading schema exists"
else
    echo "⚠ Trading schema not found. Running initialization..."
    "${SCRIPT_DIR}/init_database.sh"
fi

echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Container name: ${CONTAINER_NAME}"
echo "Database: trading_db"
echo "Port: 5433 (host) -> 5432 (container)"
echo ""
echo "To connect to the database:"
echo "  Host: localhost"
echo "  Port: 5433"
echo "  Database: trading_db"
echo "  User: postgres"
echo "  Password: (check .env file or docker-compose.yml)"
echo ""
echo "Useful commands:"
echo "  Start container:  ./scripts/start_container.sh"
echo "  Stop container:   ./scripts/stop_container.sh"
echo "  Check status:     ./scripts/check_container.sh"
echo "  View logs:        docker logs ${CONTAINER_NAME}"
echo ""

