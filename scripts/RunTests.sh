#!/bin/bash
set -e

export DATABASE_URL="sqlite:///:memory:" 

python -m pytest tests/ --disable-warnings -v