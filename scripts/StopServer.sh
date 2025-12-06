#!/bin/bash
set -e

PID_FILE="uvicorn_pid.txt"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Stopping server with PID $PID..."
    kill "$PID" || echo "Failed to kill PID $PID"
    rm -f "$PID_FILE"
else
    echo "No PID file — killing any uvicorn processes"
    pkill -f uvicorn || true
fi
