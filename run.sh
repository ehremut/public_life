#!/usr/bin/env bash
set -e

if ! command -v python3 >/dev/null; then
  echo "Python 3 is required" >&2
  exit 1
fi

if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -U pip
pip install -r requirements.txt

python -m bot.main
