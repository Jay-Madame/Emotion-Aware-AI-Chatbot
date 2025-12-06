#!/bin/bash
set -e

# --- Variables ---
VENV_DIR=".venv"
PID_FILE="uvicorn_pid.txt"
APP_MODULE="src.server:app" 
HOST="0.0.0.0"
PORT="8000"

# --- Create venv if it doesn't exist ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# --- Activate venv ---
source "$VENV_DIR/bin/activate"

# --- Install dependencies ---
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# --- Start Uvicorn server in background ---
if [ -f "$PID_FILE" ]; then
    echo "Server already running? PID file exists: $PID_FILE"
else
    echo "Starting FastAPI server..."
    uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" &
    echo $! > "$PID_FILE"
    echo "Server started with PID $(cat $PID_FILE)"
fi
