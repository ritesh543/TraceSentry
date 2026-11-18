#!/usr/bin/env bash
# Read-only hosted Studionet checks for the already deployed TraceSentry.
# Uses public address only: no private keys, signing, or test GEN necessary.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
ADDR='0x1C4C17d9A11531D7c27a3B65B24732A61E789D38'
TX='0x79b3144c72cfe26be5910307c31648ded8a365aba7e3b7ea15573c221a6ae003'
RPC='https://studio.genlayer.com/api'
command -v genlayer >/dev/null || {
  echo 'Missing GenLayer CLI. Install with: npm install -g genlayer' >&2
  exit 2
}
python3 scripts/verify_bundle.py
printf '\n=== Network (should say stable Studionet, chain ID 61999) ===\n'
genlayer network set studionet
genlayer network info
printf '\n=== Deployed contract view: get_stats() ===\n'
genlayer call "$ADDR" get_stats --rpc "$RPC"
printf '\n=== First immutable audit entry: get_audit(0, 1) ===\n'
genlayer call "$ADDR" get_audit --rpc "$RPC" --args 0 1
printf '\n=== Review tx finality and GenVM status in explorer ===\n'
printf 'https://explorer-studio.genlayer.com/tx/%s\n' "$TX"
printf '\nRead-only calls completed. Inspect results for admin, counts and DEPLOY audit.\n'
printf 'IMPORTANT: These views do NOT exercise enroll, register_lot, assess_case, or appeal writes.\n'
