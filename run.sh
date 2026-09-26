#!/usr/bin/env bash
# Full pipeline vs scratch DB (see README).
# Creds via env PG_* (defaults = local pulse compose PG, scratch DB pulsedata).
# Cross-check needs a Pulse API on the same DB: PULSE_API + PULSE_USER/PULSE_PASS.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -r requirements.txt
PG_DB="${PG_DB:-pulsedata}" .venv/bin/python run.py
