# TraceSentry v1.1 — final package test report

**18 November 2026** | Contract source `contracts/trace_sentry.py` | Python 3.13.5 | pytest 9.0.2

## Measured results in the build environment

```text
$ python3 -m py_compile contracts/trace_sentry.py
PASS

$ bash -n scripts/deploy_studionet.sh scripts/run_checks.sh scripts/smoke_deployed_readonly.sh
PASS

$ python3 -m pytest -q tests/
........................................................................ [ 73%]
..........................                                               [100%]
98 passed in 0.28s
```

**98 host-side tests passed, 0 failures.** Exactly **47** baseline v1.1 tests plus **51** additional parametrized/invariant/security/provenance cases.

The tests import the **real deployable contract file** with stubbed `genlayer` primitives, deterministic storage, synthetic accounts, a mock LLM, mock HTTPS pages, and a mock consensus callback. They cover code paths and business logic. They do **not** perform a GenVM execution.

### Additional scenarios added in final package

- Five seeded random 42-lot DAGs: independent Python reference reachability vs actual contract BFS, followed by full rollback/retraction.
- Batch sizes 1, 2, 3, 4, 7, 31, 32 and merge-node deduplication.
- Overlapping cases from **different** origin lots with overlapping downstream descendants.
- Conservative retraction with partially processed queues and risk state checks.
- Pending cases seeing descendants registered before assessment; dismissed case allows DAG updates.
- Paused processing, resumed processing, and administrator-initiated retraction while paused.
- Appeals: successful UPHOLD, invalid downgrade, absent source anchor, evidence too short, unauthorized access.
- AI decision malformed JSON schemas, severity/decision inconsistency, bool-as-int, invalid anchors, source-length check, leader/validator tolerance.
- Governance and public URL input validation, audit pagination and SHA-256 chain re-verification over 50+ records.
- Pinning to the exact v1.1 contract SHA-256 and deployment metadata consistency.

## Already observed on GenLayer Studio by user

| Gate | Evidence | Status |
|---|---|---|
| Studio v1.0 constructor | `0xf83d3fab...850c36` GenVM `Contract Error` | FAILED, historical |
| Studio v1.1 constructor | `0x79b3144c...a6ae003` accepted with GenVM `SUCCESS` | **SUCCESS / ACCEPTED** (user screenshots) |
| Studio v1.1 finality | Finalized badge not pictured | **NOT VERIFIED** |
| Studio v1.1 `get_stats()` | No real call output shared | **NOT RUN HERE** |
| Studio v1.1 participant/lot methods | No method receipt shared | **NOT RUN HERE** |
| Studio v1.1 LLM/validator and appeal methods | No method receipt shared | **NOT RUN HERE** |
| Official `genlayer-test` direct mode | No SDK installed | NOT RUN |
| `genvm-lint` | Tool unavailable | NOT RUN |
| Real Studio / GLSim integration | No network and CLI access | NOT RUN |
| Independent security audit | Not commissioned | NOT DONE |

**State of release:** deployable source is byte-for-byte unchanged from v1.1 hotfix ZIP; SHA-256 `ecb6407eed8ac0f2a24e08f49d0e52d399e830d479a94a5f1e1d6220e7a2d2ea`. The build environment **cannot** independently establish that the user's Studio upload exactly matches these bytes, as it could not download the on-chain code.

## Test next without signing

```bash
npm install -g genlayer
./scripts/smoke_deployed_readonly.sh
```

Full optional wallet/write/consensus verification is specified in `verification/LIVE_TEST_PLAN.md`. Only claim functional testnet completion once the real transaction hashes and execution traces have been captured.
