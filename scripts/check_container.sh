#!/bin/bash
# check_container.sh
# Checks if the TimescaleDB container exists and its status

set -e

CONTAINER_NAME="algo_trading_timescaledb"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "Container '${CONTAINER_NAME}' exists and is RUNNING"
        exit 0
    else
        echo "Container '${CONTAINER_NAME}' exists but is STOPPED"
        exit 2
    fi
else
    echo "Container '${CONTAINER_NAME}' does NOT exist"
    exit 3
fi

