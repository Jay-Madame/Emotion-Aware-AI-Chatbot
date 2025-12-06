#!/bin/bash
set -e

# Start the server (your StartServer.sh already handles backgrounding and PID file)
./scripts/StartServer.sh &

# Wait for server to be ready
echo "Waiting for FastAPI server to be ready..."
PORT=8000
for i in {1..30}; do
    if curl --silent http://localhost:$PORT/health > /dev/null; then
        echo "Server is ready!"
        break
    fi
    sleep 1
done

# Run tests
python -m pytest tests/
