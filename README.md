# TraceSentry

**AI-adjudicated supply-chain safety intelligence • Dependency-graph incident containment • GenLayer Intelligent Contract**

[![Python](https://img.shields.io/badge/Python-3.12%2B-2563eb)](https://www.python.org/) [![GenLayer](https://img.shields.io/badge/GenLayer-Intelligent%20Contract-7c3aed)](https://docs.genlayer.com/) [![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

TraceSentry is a standalone GenLayer Intelligent Contract for collaborative **product-lot provenance, incident verification, downstream safety warnings, and evidence-based appeals**.

> **v1.2 consensus fix (21 November 2026).** Each validator independently fetches and assesses the evidence. `assess_case` requires agreement on the exact severity that determines lot risk. A 2 (`RECALL`) versus 3 (`CRITICAL`) disagreement rejects the assessment before any case update or propagation. See [the consensus rules](docs/ARCHITECTURE.md#source-adjudication-and-consensus) and [test results](verification/TEST_REPORT.md).

## The problem

A safety notice for one raw-material shipment can affect hundreds of manufactured downstream lots. Traditional ledgers attest provenance but do not resolve whether noisy text evidence warrants a recall. TraceSentry maintains an append-only dependency graph, asks GenLayer AI validators to independently assess the evidence, then propagates alert statuses to all reachable descendants with bounded, resumable transactions. Appeals may overturn or downgrade a determination without accidentally removing unrelated, still-active notices.

## Architecture at a glance

```text
  Approved supplier                 Approved reporter / lot owner
         |                                      |
    register_lot()                           submit_case()
         |                                      |
  Immutable-parent DAG                        PENDING
         |                                      |
         |                       assess_case() — GenLayer nondet
         |                         ┌────────────┴───────────┐
         |                         │ Leader: web + LLM      │
         |                         │ Validators: fresh web  │
         |                         │ + independent LLM      │
         |                         └────────────┬───────────┘
         |                                  Agreed severity
         |                               ┌─────────┴────────┐
         |                            severity 0         severity 1..3
         |                            DISMISSED              ACTIVE
         |                                                    |
         +------------------------------------------- process_case()
                                                              |
                                                  DAG BFS, batch ≤32
                                                              |
                                                LOT ALERTS + AUDIT
                                                              |
                                                   challenge_case()
                                                              |
                                                 resolve_challenge()
                                                    /     |      \
                                                UPHOLD DOWNGRADE OVERTURN
                                                  |       |        |
                                                retain  lower   CLEAR job
                                                              |
                                                   remove ONLY this case
```

## Features

| Component | Capability |
| --- | --- |
| **Participant registry** | Self-enrollment, administrator-approved supplier/reporter roles, and revocation |
| **Provenance DAG** | Immutable directed acyclic dependencies, parent validation, bounded fan-in/fan-out |
| **Incident intake** | Source URL, declared SHA-256 metadata, category, allegation, sender permissions |
| **AI evidence review** | Live HTTPS source fetch, source-grounded exact quote, severity classification |
| **Independent consensus** | Every validator fetches and assesses evidence independently and checks the exact decision and severity |
| **Multi-case propagation** | Resumable de-duplicated BFS; processing cap of 32 lots per transaction |
| **Conservative safety** | Risk stays flagged during retraction until each lot is cleared |
| **Challenge court** | Evidence-based appeals: uphold, downgrade, or overturn with independently evaluated result |
| **Safe revocation** | Overturn clears one case's markings; overlapping cases remain intact |
| **Audit provenance** | SHA-256 hash chain over the ordered public mutation log |
| **Governance** | Pausing, revoking participants, two-step admin transfer, emergency retraction |
| **Resource guards** | Configured limits on total lots, cases, appeals, graph degree, batch and audit reads |

## Repository

```text
TraceSentry/
├── contracts/
│   └── trace_sentry.py     # Deployable, single-file GenLayer IC
├── tests/
│   ├── conftest.py         # Strict mocked GenLayer execution harness
│   ├── test_contract.py    # Core behavioral/negative/security tests
│   ├── test_extended.py    # Additional invariants, graph fuzzing and boundaries
│   └── test_release_metadata.py # Package provenance checks
├── fixes/
│   └── constructor_storage_v1.1.patch # Exact v1.0 -> v1.1 source patch
├── examples/
│   └── WALKTHROUGH.md      # Sample multi-party, multi-hop scenario
├── docs/
│   ├── ARCHITECTURE.md     # State machine, bounded work, consensus design
│   ├── INTERFACE.md        # All write / view contract methods, parameters
│   ├── DEPLOYMENT.md       # Studionet CLI + Studio UI deployment
│   └── SECURITY.md         # Threat model, known limitations and mitigations
├── scripts/
│   ├── deploy_studionet.sh # CLI deployment helper (never auto-broadcasts silently)
│   ├── run_checks.sh      # Local validation
│   ├── verify_bundle.py   # Manifest verifier
│   └── smoke_deployed_readonly.sh # Network-dependent, read-only live checks
├── verification/
│   ├── DEPLOYMENT_RESULT.json # Historical v1.1 Studio evidence
│   ├── TEST_REPORT.md      # Genuine measured results
│   ├── FAILED_STUDIO_TRANSACTION.md  # Historical failed attempt + fix
│   └── MANIFEST.sha256     # Package file integrity manifest
├── .github/workflows/tests.yml
├── requirements.txt
├── requirements-genlayer.txt
├── pytest.ini
├── Makefile
├── .gitignore
└── LICENSE
```

## Test locally (no GenLayer install required)

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -v
python3 -m py_compile contracts/trace_sentry.py
python3 scripts/verify_bundle.py
```

The host tests import the deployable source with mocked GenLayer primitives and exercise all 16 leader/validator severity pairs. GenVM lint and SDK schema validation can be run with the GenLayer tooling.

```bash
python3 -m pip install -r requirements-genlayer.txt
genvm-lint check contracts/trace_sentry.py
# Then test in Studio or GLSim and inspect real transaction traces.
```

## StudioNet deployment

v1.2 is packaged for a fresh stable StudioNet deployment (chain ID 61999). Its source hash and deployment status are in [`deployment_info.json`](deployment_info.json).

```bash
npm install -g genlayer
genlayer network set studionet
genlayer network info
# Select/unlock your disposable test wallet using the installed CLI's account commands.
# Fund it with test GEN in the GenLayer Studio faucet if required.
genlayer deploy --contract contracts/trace_sentry.py
```

Save the resulting address and transaction hash after verifying the receipt. The read-only smoke script accepts that address as its argument. See [the deployment guide](docs/DEPLOYMENT.md) and [live test plan](verification/LIVE_TEST_PLAN.md).

### Alternative: Studio UI

Open https://studio.genlayer.com → **Contracts** → **Add From File** → upload `contracts/trace_sentry.py` → **Run and Debug** → **Deploy** (no constructor arguments). Review logs and then use `get_stats()` / `enroll()` for smoke testing.

### Historical v1.1 deployment

The 18 November 2026 Studio screenshots report `ACCEPTED` and GenVM `SUCCESS` for the v1.1 constructor at `0x1C4C17d9A11531D7c27a3B65B24732A61E789D38`. Finality and subsequent method calls were unverified. The v1.1 constructor fixed the typed storage initialization failure from v1.0. [Historical deployment record](verification/DEPLOYMENT_RESULT.json) · [v1.0 diagnosis](verification/FAILED_STUDIO_TRANSACTION.md)

## Contract usage overview

1. Supplier and reporter accounts call `enroll(organization, descriptor)`.
2. Admin approves roles with `configure_participant(address, supplier, reporter, approved)`.
3. Suppliers call `register_lot(lot_id, label, product_code, parents_json, manifest_hash)`; use `"[]"` for a root lot.
4. An authorized caller submits `submit_case(lot_id, category, allegation, evidence_url, evidence_sha256)`.
5. A transaction calls `assess_case(case_id)`; consensus classifies risk.
6. Any actor can call `process_case(case_id, 32)` repeatedly until `mode == "DONE"`.
7. Downstream lots reveal effective exposure via `get_lot_risk(lot_id)`.
8. An eligible actor challenges; `resolve_challenge(appeal_id)` applies independently validated rebuttal evidence.
9. For overturn, call `process_case(case_id, 32)` repeatedly until every propagated mark has been removed.

See the complete [method specification](docs/INTERFACE.md) and [walkthrough](examples/WALKTHROUGH.md).

## Tradeoffs and explicit boundaries

* This is **advisory safety alert infrastructure**, not a certified legal/medical/regulatory recall decision engine. Product safety decisions require human review and authoritative evidence.
* **No tokens and no escrow** are handled. The GEN wallet funds network transactions only.
* User-supplied `evidence_sha256` and `manifest_hash` are metadata commitments; this contract **does not cryptographically verify off-chain bytes** against those hashes.
* The URL check is a first-level input filter, **not complete SSRF / DNS rebinding / redirect protection**.
* Case propagation is **not automatic** — somebody must process its pending batches. A globally blocked DAG write while jobs remain prevents late edges from escaping propagation.
* The protocol has a trusted administrator for role approvals, pause, and emergency retraction. It is **not fully decentralized governance**.

## References

* GenLayer developer docs: https://docs.genlayer.com/developers/intelligent-contracts/
* Equivalence principle: https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
* Storage: https://docs.genlayer.com/developers/intelligent-contracts/features/storage
* CLI deployment: https://docs.genlayer.com/developers/intelligent-contracts/deploying/cli-deployment

**License:** MIT. This is a new original project; not a fork of GrantOverlap.
