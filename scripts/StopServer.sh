#!/bin/bash
kill $(cat uvicorn_pid.txt)
rm uvicorn_pid.txt
