#!/bin/sh
set -eu

python3 -m compileall -q main.py board_preview.py opening_trainer tests
python3 -m pytest -q
git --no-pager status --short
