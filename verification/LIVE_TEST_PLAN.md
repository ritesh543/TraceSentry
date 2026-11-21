# TraceSentry v1.2 live contract test plan

Use the address and transaction hash from deploying the v1.2 source on stable StudioNet (chain ID 61999). Record the receipt in [the release metadata](../deployment_info.json).

The 18 November 2026 screenshots record a v1.1 constructor transaction. [Historical v1.1 deployment record](DEPLOYMENT_RESULT.json)

## Checks executable without signing

With the GenLayer CLI installed, set `ADDR` to your v1.2 deployment address and run `./scripts/smoke_deployed_readonly.sh "$ADDR"`. Review the two returned views and the deployment receipt.

1. Read `get_stats` and verify the expected administrator, `audit_entries >= 1`, and non-negative counters.
2. Read `get_audit(0, 1)` and verify the first event is `DEPLOY` with the deployer's address.
3. Inspect the new deployment transaction in the explorer for GenVM `SUCCESS` and record its current finality status.
4. Where the CLI supports source retrieval, compare the retrieved source to `contracts/trace_sentry.py`.

## Stateful write-method tests — perform in hosted Studio using disposable test wallets

**Warning:** These writes permanently modify this test contract's state and can incur test GEN fees. Run on a separate fresh deployment if you need repeatable empty-state invariants. No wallet private keys are required in this repository.

| ID | Actor | Action | Assertions / evidence to capture | Status |
|---|---|---|---|---|
| LIVE-01 | viewer | `get_stats()` | `audit_entries >= 1`, expected admin / counters | PENDING |
| LIVE-02 | supplier | `enroll("Sample Demo Supplier", "Responsible for independently verified lot provenance")` | accepted; `get_participant()` returns pending approval | PENDING |
| LIVE-03 | admin | `configure_participant(<supplier>, true, false, true)` | accepted; supplier approved, reporter false | PENDING |
| LIVE-04 | supplier | `register_lot("pilot-root-01", "Pilot verified batch", "PILOT001", "[]", "ab" repeated 32)` | accepted; `get_lot()` returns parent `[]` | PENDING |
| LIVE-05 | supplier | register child lot with parents JSON `'["pilot-root-01"]'` | child dependency visible via `get_children()` | PENDING |
| LIVE-06 | viewer | `get_lot_risk("pilot-root-01")` | severity 0 before a real incident | PENDING |
| LIVE-07 | unapproved wallet | try to `register_lot` | rejected with authorization error | PENDING |
| LIVE-08 | supplier | `submit_case(...)` with a **real publicly accessible HTTPS evidence source** | accepted; pending case, `get_case` has ID | PENDING |
| LIVE-09 | any caller | `assess_case("case-0001")` (or ID returned above) | On acceptance, check the exact stored severity in `get_case` and the audit. On rejection, verify the case is still pending and no propagation job was created. | PENDING |
| LIVE-10 | any caller | if `ACTIVE`, call `process_case(case_id, 1..32)` repeatedly | `pending_jobs` decreases; descendants flagged and queue ends `DONE` | PENDING |
| LIVE-11 | supplier or approved reporter | if `ACTIVE`, submit verifiable rebuttal with `challenge_case` | accepted; challenge state visible | PENDING |
| LIVE-12 | any caller | `resolve_challenge(appeal_id)` | accepted consensus / explicit error; `get_challenge()` shows action | PENDING |
| LIVE-13 | any caller | if `OVERTURN`, repeatedly `process_case(case_id, 1..32)` | only case-specific marks removed; other alerts preserved | PENDING |
| LIVE-14 | admin | pause/unpause and two-step admin handoff on a **separate** disposable deployment | authorization and governance behavior as documented | PENDING |

### Example view commands

```bash
genlayer network set studionet
genlayer network info

ADDR='YOUR_V1_2_CONTRACT_ADDRESS'
genlayer call "$ADDR" get_stats --rpc https://studio.genlayer.com/api
genlayer call "$ADDR" get_audit --rpc https://studio.genlayer.com/api --args 0 1
```

### Example of the first **optional** write calls (never run automatically)

```bash
# Select / unlock the appropriate disposable wallet using the Studio UI or CLI.
ADDR='YOUR_V1_2_CONTRACT_ADDRESS'
# In supplier wallet:
genlayer write "$ADDR" enroll --args "Sample Demo Supplier" "Responsible for independently verified lot provenance"
# Switch to deployer/admin wallet; insert the actual supplier PUBLIC address:
genlayer write "$ADDR" configure_participant --args 0xSUPPLIER_ADDRESS true false true
# Switch back to supplier wallet, and confirm contract ID is still unused:
genlayer write "$ADDR" register_lot --args "pilot-root-01" "Pilot verified batch" "PILOT001" '[]' "$(printf 'ab%.0s' {1..32})"
```

Commands above are illustrative and must not be mistaken for executed transactions. Later AI assessment is inherently non-deterministic and might dismiss a weak source; the test should assert a **valid consensus decision** rather than a predetermined severity.

## Limitations of the offline suite

The bundled Python tests import the actual contract code but mock `genlayer`, storage and consensus. They are not the official `genlayer-test` direct mode, GLSim, GenVM, live RPC or a production security audit. In particular, they do not check transaction rollback atomicity, RPC serialization, GenVM nondeterministic web/LLM behavior, real validator equivalence, fee usage, or network-side state finality.
