#!/bin/bash
chmod 700 scripts/chmodAllScripts.sh
python3 -m venv .venv
source .venv/bin/activate
./scripts/chmodAllScripts.sh
./scripts/InstallDependencies.sh
./scripts/StartServer.sh
./scripts/RunTests.sh
./scripts/StopServer.sh
