# Security assessment and trust boundaries

## Current status

Experimental. v1.2 passed host tests and GenVM lint and SDK schema validation. Live StudioNet verification and an independent security audit are pending. See [the test report](../verification/TEST_REPORT.md).

## Covered by the tests

1. Sender-based authorization and revocation; two-step administrator handoff.
2. Duplicate lot rejection, parent validation, self-cycle rejection, graph degree limits.
3. Input length, ID, URL scheme and digest syntax validation.
4. Rejection of every disagreement between valid severity levels, including `RECALL` and `CRITICAL`, before case, job, or audit writes.
5. Anchored evidence output, rejection of invented quotations.
6. Overlap-safe BFS alert propagation and bounded per-tx processing.
7. Conservative retractions, appeals, overlapping alerts and idempotence guards.
8. Pausing and tamper-evident audit hash link.

## Known limitations

- **Role centralization:** Administrator grants roles and may emergency-retract after propagation. Users need to trust or govern this key. For production: multisig/governance and time delays.
- **Evidence custody:** Source URLs are fetched live; pages may change or disappear. The posted `evidence_sha256` is a declarative commitment only, **not verified from fetched bytes**. For production, add trustworthy content snapshots and stable digests.
- **Web SSRF:** `_url` blocks obvious local addresses, userinfo and ports, but redirect chains, hostname-to-private-IP resolution, noncanonical IP forms and encoded host tricks require network-side egress control.
- **Prompt injection:** Untrusted source may embed instructions; the prompt explicitly ignores them, but source-grounded independent LLM checks are not complete protection against coordinated false conclusions.
- **Source quality:** HTTPS and anchored quotes do not make a source authoritative. False published claims remain possible. Use official notices and multi-source independent corroboration.
- **Chain timing:** `pending_jobs` is not autonomously drained; a party needs to pay for/submit batches. An unfinished job can prevent DAG edits.
- **Visible private data:** Source URLs, descriptions, allegations, audit records and organization metadata are public. Never store confidential patient/customer records or secrets.
- **Bounded size:** 512 lots, 128 cases, 256 challenges, max fan-in 6, max fan-out 24; repeated large-case views can be expensive. Audit records are unbounded; production needs archival strategy.
- **Appeals:** One challenge per case. After that, only admin can issue emergency retraction; governance remains a point of trust.
- **No challenge window:** Once `ACTIVE`, propagation may proceed before the originating party challenges. Design intentionally prioritizes containment; choose a legal escalation policy off-chain.
- **Nondeterminism:** Different source versions or LLM differences can cause failed consensus. No promise of finality or acceptance is made without live Studio tests.
- **GenVM runtime:** SDK schema validation checks the pinned runtime's contract interface. The live test plan exercises actual transaction execution and network consensus. [Live test plan](../verification/LIVE_TEST_PLAN.md)
- **Hash integrity:** SHA-256 audit chaining detects mutation against trusted published root but is not a signature and does not prove source or actor honesty.

## Before real deployment

1. Run `genvm-lint check contracts/trace_sentry.py` with matching CLI/runtime.
2. Execute GenLayer direct-mode tests plus Studio/GLSim integration cases.
3. Test independent web/LLM reviewers, rejected consensus, reorg/revert and fees.
4. Test URLs with redirect chains and malicious/prompt-injected page content.
5. Verify pagination and storage costs near configured graph/case limits.
6. Obtain third-party audit of authorization, partial batches, data integrity and liveness.
7. Formalize incident escalation, factual corroboration, and human-in-the-loop review.
