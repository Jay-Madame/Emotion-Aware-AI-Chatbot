#!/bin/bash
set -e

# Start the server (your StartServer.sh already handles backgrounding and PID file)
./scripts/StartServer.sh &
SERVER_PID=$!

sleep 5

# Run tests
export DATABSE_URL="sqlite:///:memory:"

python -m pytest tests/ --disable-warnings -v
