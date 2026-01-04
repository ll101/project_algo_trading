#!/bin/bash
# stop_container.sh
# Stops the TimescaleDB container gracefully

set -e

CONTAINER_NAME="algo_trading_timescaledb"

echo "Stopping TimescaleDB container..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running."
    exit 1
fi

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container '${CONTAINER_NAME}' does not exist."
    exit 0
fi

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker stop "${CONTAINER_NAME}" > /dev/null 2>&1
    echo "Container '${CONTAINER_NAME}' stopped successfully."
else
    echo "Container '${CONTAINER_NAME}' is already stopped."
fi

