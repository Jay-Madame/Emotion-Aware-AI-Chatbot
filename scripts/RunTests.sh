#!/bin/bash
set -e

# Start the server (your StartServer.sh already handles backgrounding and PID file)
./scripts/StartServer.sh &
SERVER_PID=$!

sleep 5

# Run tests
python -m pytest tests/
