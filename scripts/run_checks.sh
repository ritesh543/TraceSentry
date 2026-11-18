#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
python3 -m py_compile contracts/trace_sentry.py
python3 -m pytest -v tests/
if command -v genvm-lint >/dev/null; then
  genvm-lint check contracts/trace_sentry.py
else
  printf '\nNOTICE: genvm-lint unavailable; GenVM compatibility NOT validated.\n' >&2
fi
