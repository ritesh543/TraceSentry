#!/usr/bin/env bash
# Read-only hosted Studionet checks for a supplied TraceSentry address.
# Uses public address only: no private keys, signing, or test GEN necessary.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ $# -ne 1 || ! ${1:-} =~ ^0x[0-9a-fA-F]{40}$ ]]; then
  echo 'Usage: bash scripts/smoke_deployed_readonly.sh <contract-address>' >&2
  exit 2
fi
ADDR="$1"
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
printf '\nRead-only calls completed. Inspect results for admin, counts and DEPLOY audit.\n'
printf 'IMPORTANT: These views do NOT exercise enroll, register_lot, assess_case, or appeal writes.\n'
