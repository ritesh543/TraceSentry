# Contract API reference

All writes are GenLayer transactions. Public views are read-only. `parents_json` is a JSON **string**, not a list argument.

## Governance / people

| Method | Inputs | Permission | Effect |
|---|---|---|---|
| `enroll` | `organization: str, descriptor: str` | unregistered caller | creates unapproved organization |
| `configure_participant` | `account: str, supplier: bool, reporter: bool, approved: bool` | admin | assigns approved SUPPLIER and/or REPORTER roles |
| `set_paused` | `value: bool` | admin | blocks general mutations until resumed |
| `propose_admin` | `new_admin: str` | admin | nominates successor |
| `accept_admin` | none | nominee | accepts admin rights |

## Lots / cases

| Method | Inputs | Permission | Result |
|---|---|---|---|
| `register_lot` | `lot_id, label, product_code, parents_json, manifest_hash` (all strings) | approved supplier | creates immutable lot with parent DAG edges |
| `submit_case` | `lot_id, category, allegation, evidence_url, evidence_sha256` (strings) | lot origin custodian, reporter, or admin | returns case id like `case-0001` |
| `assess_case` | `case_id: str` | any while unpaused | independent evidence assessment with exact decision and severity agreement |
| `process_case` | `case_id: str, batch: u32` | any while unpaused | BFS propagation / case-specific retraction in chunks ≤32 |
| `challenge_case` | `case_id, rebuttal_url, rebuttal_sha256, argument` (strings) | origin custodian, reporter, or admin | returns appeal id like `appeal-0001` |
| `resolve_challenge` | `challenge_id: str` | any while unpaused | independent assessment of both sources and the recorded argument, with exact action and severity agreement |
| `emergency_retract` | `case_id: str, reason: str` | admin | starts conservative clearing of finished active incident |

`category` must be one of `CONTAMINATION`, `COUNTERFEIT`, `TRANSPORT`, `COMPLIANCE`, `OTHER`. `evidence_url` must be a public HTTPS URL, with additional syntactic restrictions. SHA-256 should be **64 hex characters**. Manifest hash accepts 16–128 hex characters.

## Read methods

| Method | Returns |
|---|---|
| `get_lot(lot_id)` | immutable lot record with parents, label, custodian, manifest metadata |
| `get_children(lot_id)` | directly dependent lot IDs |
| `get_lot_risk(lot_id)` | `{severity, classification, case_ids}` |
| `get_case(case_id)` | all incident state, queue and cursor |
| `get_challenge(challenge_id)` | all appeal details / verdict |
| `get_participant(account)` | organization, roles and approval state |
| `get_stats()` | object counts, pending job count, pause, audit root, admin |
| `get_audit(start: u32,limit: u32)` | pages of hash-linked audit entries (1..32) |

## Example

```python
# Example input values in Studio — transaction calls occur under different accounts.
# Step 1: caller enrolls
# enroll("Global Cold Storage", "Temperature controlled product custodian")
# Step 2: admin authorizes the caller with configure_participant(...,True,False,True)
# Step 3: enrolled supplier submits a root lot:
register_lot("milk-001", "Bottled batch 001", "MILK-PREMIUM", "[]", "a" * 64)
# Step 4: another supplier submits a derived lot:
register_lot("cheese-002", "Cheese batch 002", "CHEESE-A", '["milk-001"]', "b" * 64)
# Step 5: permitted reporter submits an actual publicly accessible evidence URL
# submit_case("milk-001", "CONTAMINATION", "...20+ chars...", "https://...", "<64hex>")
# Step 6: assess_case("case-0001") ; process_case("case-0001", 32)
# Step 7: get_lot_risk("cheese-002")
```

**Note:** The code block is illustrative pseudo-interaction (no imported client), not a script directly runnable with standard Python.
