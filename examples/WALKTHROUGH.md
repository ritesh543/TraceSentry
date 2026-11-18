# End-to-end example: temperature-sensitive vaccine packaging

This fictional scenario shows the state machine, **not** a real-world health claim.

A logistics operator creates `batch-raw-001`, whose insulated bags feed `shipment-eu-002` and `shipment-apac-003`. A final distributor creates `retail-pack-004` using `shipment-eu-002`.

```text
batch-raw-001  ──>  shipment-eu-002  ──>  retail-pack-004
           └──>  shipment-apac-003
```

All suppliers must enroll and be explicitly approved by the deployer/admin. They register lots using their wallet addresses and parent IDs already on chain. Each lot has an externally computed manifest SHA-256.

A reporter registers an incident against `batch-raw-001` with a public HTTPS bulletin. Once validators agree on severity 3, the `process_case` queue advances in chunks. The first step marks `batch-raw-001` and enqueues its two children; the next steps flag those children and `retail-pack-004`. Effective descendant status becomes `CRITICAL`.

Suppose an independent laboratory publishes a corrected report, and a supplier submits a challenge with the updated URL. If leader and validator independently reach `OVERTURN`, a second bounded job unmarks the incident throughout the graph. If `shipment-eu-002` also has an **unrelated** active transport violation, that case's status remains untouched.

### Suggested Studio calls

```text
[Supplier account]
enroll("Acme Demo Logistics", "Operates simulated temperature-controlled shipments")

[Admin account]
configure_participant("0x<SUPPLIER_ADDRESS>", true, false, true)

[Supplier account]
register_lot("batch-raw-001", "Insulation materials", "INS-001", "[]", "<sha256 hex>")
register_lot("shipment-eu-002", "EU demo shipment", "SHIP-EU", "[\"batch-raw-001\"]", "<sha256 hex>")
register_lot("shipment-apac-003", "APAC demo shipment", "SHIP-AP", "[\"batch-raw-001\"]", "<sha256 hex>")
register_lot("retail-pack-004", "Retail packaging", "RETAIL-1", "[\"shipment-eu-002\"]", "<sha256 hex>")

[Approved reporter or original custodian]
submit_case("batch-raw-001", "TRANSPORT", "Detailed supported allegation at least 20 characters", "https://<real-evidence-host>/notice", "<sha256 hex>")

[Anyone]
assess_case("case-0001")
process_case("case-0001", 32) # call again if not DONE
get_lot_risk("retail-pack-004")
```

The real AI classification depends on evidence quality, validators, and network consensus. This guide does not guarantee that an allegation is upheld.
