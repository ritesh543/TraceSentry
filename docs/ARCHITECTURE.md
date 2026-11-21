# Design and invariants

## Data plane

Each lot is a JSON record under `TreeMap[str,str]` and is immutable after registration. Parent references can target **existing** lots only. Edges always point from earlier-created parents to newly-created children, so graph cycles cannot form. One parent has at most 24 children, one lot may have at most six parents, and there are at most 512 lots overall. Registration is disabled while any incident spread/retract queue is incomplete, to prevent new graph edges from escaping an existing traversal.

### State model

| Object | States / transition |
|---|---|
| Case | `PENDING → DISMISSED` OR `PENDING → ACTIVE → RETRACTING → CLEARED` |
| Spread job | `NONE → SPREAD → DONE`; after overturn: `DONE → CLEAR → DONE` |
| Challenge | `PENDING → RESOLVED` (UPHOLD / DOWNGRADE / OVERTURN) |
| Lot | No mutable status field; effective severity is derived from attached live cases |

### Persistent state

- `participants`: account → approval + authorized roles + organization metadata.
- `lots`, `children`: immutable lot body and adjacency lists.
- `cases`, `challenges`: case and appeal state machine records.
- `case_seen`: deduplication tags keyed by case + lot.
- `lot_alerts`: list of case references attached to each lot; max effective risk derived at view time.
- `audit`, `audit_root`: append-only JSON event log and hash-chain root.
- `pending_jobs`: number of incomplete propagation or retraction jobs.

## Source adjudication and consensus

A case leader fetches public HTTPS evidence with `gl.nondet.web.render(url, mode="text")`, limits it to 12,000 characters, and requests a structured `{decision,severity,anchor,rationale}` assessment. Each validator fetches its own copy, verifies the leader's quote against that copy, and independently assesses the same copy. It compares the substantiation decision and the exact integer severity. Explanations and quotes can vary in independently generated responses.

Consensus binds the value written to the case and used for the maximum severity returned by `get_lot_risk`. A mismatch rejects the assessment before the contract stores a case outcome, starts a job, or appends the assessment audit entry.

| Severity | Lot risk at that level | Evidence criterion |
| --- | --- | --- |
| 0 | `CLEAR` | The allegation lacks substantiation |
| 1 | `WATCH` | A credible concern warrants monitoring |
| 2 | `RECALL` | Evidence warrants product withdrawal |
| 3 | `CRITICAL` | An immediate serious hazard requires urgent containment |

The appeal leader and validators fetch both sources independently and assess the challenger's recorded argument against them. Each validator verifies the proposed quote on the evidence it assessed, then requires exact agreement on the action and severity. The case transitions only when the outcome is within the allowed severity range for its prior level.

The prompts treat allegations, appeal arguments, and source documents as untrusted input. Independent review and quote checks can reduce prompt-injection risk. Shared-model failures and misleading evidence remain possible.

## Bounded fault containment

A `SPREAD` job is a breadth-first search over the directed lot DAG. The job persists `queue`, `cursor`, and `case_seen` entries. Each `process_case(case_id,batch)` handles 1..32 nodes, adds the case reference, queues new children at most once, and commits progress. Any actor may continue the work.

If two incidents reach the same lot, `lot_alerts` stores **both** references. `get_lot_risk` computes the maximum severity among still-active incidents. This prevents an overturned case from erasing the warning created by another case.

When overturned, the finished queue is reused for **retraction** (`CLEAR`); the contract removes only that case's marks, in bounded batches. During retraction, the old severity persists for nodes not yet cleared: safety does not rely on a single atomic unbounded rollback.

Global DAG edit freeze (`pending_jobs > 0`) is deliberately conservative. It is a liveness tradeoff; an abandoned job can block registrations. Operators should monitor `get_stats().pending_jobs` and process pending queues.

## Integrity chain

Each audit record includes previous root, sequence number, transaction time, actor, event, and payload. The new root is `sha256(canonical_json(record))`. `get_audit(start,limit)` supports independent, bounded log verification. The audit chain is **tamper-evident relative to the published state**, not external proof that evidence was truthful.

## Scalability

Maximum deployment data size is bounded but expensive. Storage remains on-chain, and each case retains a queue of at most 512 vertices. View calls computing risk load references and related case objects. For bigger real-world supply graphs, consider sharding by product family/period and signed bridge attestations; do not silently remove these bounds.
