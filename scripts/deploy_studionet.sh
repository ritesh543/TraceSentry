#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
command -v genlayer >/dev/null || { echo 'GenLayer CLI not found. Run: npm install -g genlayer' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'python3 required' >&2; exit 1; }
python3 -m py_compile contracts/trace_sentry.py
printf '\nTraceSentry StudioNet deploy — NO LIVE DEPLOYMENT OCCURRED YET\n'
genlayer network set studionet
genlayer network info
printf '\nVerify: stable Studionet / chain id 61999; check signer wallet and fees.\n'
printf 'To inspect wallet help: genlayer account --help\n'
read -r -p 'Broadcast deployment transaction now? Type DEPLOY: ' answer
if [[ "$answer" != 'DEPLOY' ]]; then
  echo 'Cancelled. No deployment transaction requested.'
  exit 0
fi
genlayer deploy --contract contracts/trace_sentry.py
printf '\nIf the transaction succeeded, verify its finality and on-chain execution result.\n'
