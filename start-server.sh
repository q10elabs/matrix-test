#!/bin/bash

# Start Synapse Matrix server in the background
# Synapse manages its own PID file via the pid_file config option

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Create log directory if it doesn't exist
mkdir -p server/logs

# Start server in background, redirecting output to log file
echo "Starting Synapse server..."
python -m synapse.app.homeserver --config-path server/homeserver.yaml > server/logs/synapse.log 2>&1 &

echo "Synapse server started"
echo "Log file: server/logs/synapse.log"
echo "PID file: /tmp/synapse.pid (managed by Synapse)"
