#!/bin/bash
set -e

# Start the server (your StartServer.sh already handles backgrounding and PID file)
./scripts/StartServer.sh &
SERVER_PID=$!

sleep 5

# Run tests
export TESTING=1
python -m pytest tests/
