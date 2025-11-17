#!/bin/bash

# Stop Synapse Matrix server
# Reads PID from the file managed by Synapse

PID_FILE="/tmp/synapse.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Error: PID file not found at $PID_FILE"
    echo "Server may not be running"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Error: Process with PID $PID is not running"
    exit 1
fi

echo "Stopping Synapse server (PID: $PID)..."
kill "$PID"

# Wait for process to terminate
timeout 10 tail --pid=$PID -f /dev/null 2>/dev/null || true

if kill -0 "$PID" 2>/dev/null; then
    echo "Process did not stop gracefully, force killing..."
    kill -9 "$PID"
fi

echo "Synapse server stopped"
