#!/bin/bash
uvicorn src.server:app --host 0.0.0.0 --port 8000 &
echo $!` > uvicorn_pid.txt
sleep 3
