#!/bin/bash
set -e

PID_FILE="uvicorn_pid.txt"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Stopping server with PID $PID..."
    kill "$PID" || echo "Failed to kill PID $PID, maybe it's already stopped."
    rm -f "$PID_FILE"
    echo "Server stopped."
else
    echo "No server PID file found. Trying to stop uvicorn processes..."
    pkill -f uvicorn || echo "No uvicorn processes found."
fi
