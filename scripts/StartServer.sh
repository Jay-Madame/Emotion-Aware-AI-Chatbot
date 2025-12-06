#!/bin/bash
set -e

VENV_DIR=".venv"
PID_FILE="uvicorn_pid.txt"
APP_MODULE="src.server:app"
HOST="0.0.0.0"
PORT="8000"

# --- Activate virtual environment ---
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# --- Remove stale PID file if process is dead ---
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "Stale PID file found. Removing..."
        rm -f "$PID_FILE"
    else
        echo "Server already running with PID $PID"
        exit 0
    fi
fi

# --- Start FastAPI server in background ---
echo "Starting FastAPI server..."
uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" > uvicorn.log 2>&1 &

PID=$!
echo $PID > "$PID_FILE"

sleep 2

# --- Optional quick check ---
if ! curl --silent http://localhost:$PORT/ > /dev/null; then
    echo "❌ ERROR: Server failed to start. Check uvicorn.log"
    cat uvicorn.log
    rm -f "$PID_FILE"
    exit 1
fi

echo "Server started successfully with PID $PID"
