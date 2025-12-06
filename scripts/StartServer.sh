#!/bin/bash
set -e

VENV_DIR=".venv"
PID_FILE="uvicorn_pid.txt"
APP_MODULE="src.server:app"
HOST="0.0.0.0"
PORT="8000"

source "$VENV_DIR/bin/activate"

echo "Starting FastAPI server..."
uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" > uvicorn.log 2>&1 &

PID=$!
echo $PID > "$PID_FILE"
sleep 2
echo "Server started with PID $PID"
