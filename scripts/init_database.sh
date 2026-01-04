#!/bin/bash
# init_database.sh
# Initializes the database schema (runs SQL scripts)
# Note: init.sql runs automatically on first container creation,
# but this script can be used to re-run initialization if needed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"
CONTAINER_NAME="algo_trading_timescaledb"

echo "Initializing database schema..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container '${CONTAINER_NAME}' is not running."
    echo "Please start it first with: ./scripts/start_container.sh"
    exit 1
fi

# Wait for database to be ready
echo "Waiting for database to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker exec "${CONTAINER_NAME}" pg_isready -U postgres -d trading_db > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo "Error: Database did not become ready in time."
    exit 1
fi

# Run the initialization SQL script
if [ -f "${DOCKER_DIR}/init.sql" ]; then
    echo "Running initialization SQL script..."
    docker exec -i "${CONTAINER_NAME}" psql -U postgres -d trading_db < "${DOCKER_DIR}/init.sql"
    echo "Database initialization completed successfully!"
else
    echo "Warning: init.sql not found at ${DOCKER_DIR}/init.sql"
    echo "Skipping SQL initialization."
fi

