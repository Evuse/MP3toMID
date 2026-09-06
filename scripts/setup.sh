#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 11), "TuneMorph requires Python 3.11 or newer"'

if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt

printf '\nTuneMorph backend installed with: '
.venv/bin/python -c 'import sys, tunemorph_backend; print(sys.executable, tunemorph_backend.__version__)'
printf "Start it with: make backend\n"
