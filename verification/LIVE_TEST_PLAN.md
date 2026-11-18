# TraceSentry — Remaining live contract test plan

**Existing contract:** `0x1C4C17d9A11531D7c27a3B65B24732A61E789D38`  
**Network:** GenLayer hosted Studionet, chain ID 61999  
**Deployment tx:** `0x79b3144c72cfe26be5910307c31648ded8a365aba7e3b7ea15573c221a6ae003`

## Evidence already collected

The user's 18 November 2026 Studio Explorer screenshots show:

- Transaction **ACCEPTED**, type Deploy, with 5 initial validators.
- Consensus result **Accepted**.
- GenVM Execution **SUCCESS**, result code **Return**, return value `null`, stderr empty.

This is direct evidence of successful **constructor execution**, not evidence of full method coverage, transaction finality, or correctness of all later workflows. The contract file in this repository matches the previous fixed v1.1 ZIP by SHA-256; the on-chain source has **not** been independently retrieved and compared.

## Checks executable without signing

Requires working internet and GenLayer CLI. `./scripts/smoke_deployed_readonly.sh` attempts the following against the **existing** address, with no writes:

1. `genlayer call <address> get_stats` — verify a JSON object, expected `admin` equals deployer unless governance has changed, `audit_entries >= 1`, counters non-negative.
2. `genlayer call <address> get_audit --args 0 1` — verify first event is `DEPLOY` and actor / data are correct.
3. On Explorer, inspect this exact tx for **FINALIZED** (if it has progressed) and GenVM `SUCCESS`. Do not equate `ACCEPTED` with `FINALIZED`.
4. Optionally, use `genlayer code <address>` and independently compare the source to `contracts/trace_sentry.py`; output formatting varies by CLI version.

These have **not been executed in the ChatGPT container**, because its GenLayer CLI and outbound DNS / RPC access are unavailable.

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
| LIVE-09 | any caller | `assess_case("case-0001")` (or ID returned above) | validator consensus, GenVM `SUCCESS`, outcome validated or explicit rejection | PENDING |
| LIVE-10 | any caller | if `ACTIVE`, call `process_case(case_id, 1..32)` repeatedly | `pending_jobs` decreases; descendants flagged and queue ends `DONE` | PENDING |
| LIVE-11 | supplier or approved reporter | if `ACTIVE`, submit verifiable rebuttal with `challenge_case` | accepted; challenge state visible | PENDING |
| LIVE-12 | any caller | `resolve_challenge(appeal_id)` | accepted consensus / explicit error; `get_challenge()` shows action | PENDING |
| LIVE-13 | any caller | if `OVERTURN`, repeatedly `process_case(case_id, 1..32)` | only case-specific marks removed; other alerts preserved | PENDING |
| LIVE-14 | admin | pause/unpause and two-step admin handoff on a **separate** disposable deployment | authorization and governance behavior as documented | PENDING |

### Example view commands

```bash
genlayer network set studionet
genlayer network info

ADDR=0x1C4C17d9A11531D7c27a3B65B24732A61E789D38
genlayer call "$ADDR" get_stats --rpc https://studio.genlayer.com/api
genlayer call "$ADDR" get_audit --rpc https://studio.genlayer.com/api --args 0 1
```

### Example of the first **optional** write calls (never run automatically)

```bash
# Select / unlock the appropriate disposable wallet using the Studio UI or CLI.
ADDR=0x1C4C17d9A11531D7c27a3B65B24732A61E789D38
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
