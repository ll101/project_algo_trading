#!/bin/bash
# start_container.sh
# Starts the TimescaleDB container if it exists

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"
CONTAINER_NAME="algo_trading_timescaledb"

echo "Starting TimescaleDB container..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container '${CONTAINER_NAME}' does not exist."
    echo "Please run './scripts/setup_docker.sh' first to create the container."
    exit 1
fi

# Start the container
if docker start "${CONTAINER_NAME}" > /dev/null 2>&1; then
    echo "Container '${CONTAINER_NAME}' started successfully."
    
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker exec "${CONTAINER_NAME}" pg_isready -U postgres -d trading_db > /dev/null 2>&1; then
            echo "Database is ready!"
            exit 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    echo "Warning: Database may not be fully ready yet. Please check manually."
    exit 0
else
    echo "Error: Failed to start container '${CONTAINER_NAME}'"
    exit 1
fi

