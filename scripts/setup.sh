#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 11), "TuneMorph requires Python 3.11 or newer"'

if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt

if ! command -v ffprobe >/dev/null 2>&1; then
  printf '\nWARNING: ffprobe was not found. Install FFmpeg (macOS: brew install ffmpeg) '
  printf 'before uploading MP3, M4A, or FLAC files.\n'
fi

printf '\nTuneMorph backend installed with: '
.venv/bin/python -c 'import sys, tunemorph_backend; print(sys.executable, tunemorph_backend.__version__)'
printf "Start it with: make backend\n"
