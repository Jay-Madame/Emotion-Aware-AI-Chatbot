#!/bin/bash
set -e

VENV_DIR=".venv"
PID_FILE="uvicorn_pid.txt"
APP_MODULE="src.server:app"
HOST="0.0.0.0"
PORT="8000"

# Activate venv
source "$VENV_DIR/bin/activate"

# If PID file exists but process is dead → remove it
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

echo "Starting FastAPI server..."
uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" > uvicorn.log 2>&1 &

PID=$!
echo $PID > "$PID_FILE"

sleep 2

# Verify server is running
if ! curl --silent http://localhost:$PORT/ > /dev/null; then
    echo "❌ ERROR: Server failed to start. Check uvicorn.log:"
    echo "-----------------------------------------------"
    cat uvicorn.log
    echo "-----------------------------------------------"
    rm -f "$PID_FILE"
    exit 1
fi

echo "Server started successfully with PID $PID"
