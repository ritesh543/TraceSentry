# Studio deployment attempt: finalized transaction with GenVM failure

**Transaction:** `0xf83d3faba96fcaef72b70d65763232e705411b23b86b29dc746f41b350850c36`  
**Explorer:** https://explorer-studio.genlayer.com/tx/0xf83d3faba96fcaef72b70d65763232e705411b23b86b29dc746f41b350850c36  
**Reported by developer:** 18 November 2026

## Observed result (from user-provided Studio Explorer screenshots and stderr)

- Status: `FINALIZED` (transaction lifecycle only).
- Type: `Deploy`.
- GenVM execution result: `ERROR`.
- Result code: `Contract Error`.
- Error message: `exit_code 1`.
- Root traceback: `contracts/trace_sentry.py` prior file, `__init__`, `self.case_seen = TreeMap()`; storage setter raises `AssertionError: Is right the same storage type? TreeMap <- TreeMap`.

**Interpretation: deployment execution failed. `FINALIZED` is not proof that the contract initialized successfully. The address displayed in the failed deploy transaction must NOT be represented as a working contract.**

## Patch in this package

All `TreeMap` fields and the `DynArray` field are defined with fully specialized type annotations and are **implicitly zero-initialized by GenVM**. `__init__` no longer assigns `TreeMap()` or `DynArray[str]()` to them. The audit log is initialized through its first `.append()`.

A stricter host mock now rejects direct generic storage construction and lazily provides zero-initialized annotated collections, catching the former deployment bug in local tests.

## Historical verification checklist — subsequently resolved on 18 November 2026

1. **Done by user:** Reopened Studio and deployed corrected v1.1 from file.
2. Create a **new** deploy transaction. Do not use the old transaction hash/address as proof.
3. Inspect **GenVM Execution Result** and **stderr**, not only transaction status.
4. Read `get_stats()` on the new contract. Expected: `lots=0`, `cases=0`, `challenges=0`, `pending_jobs=0`, `audit_entries=1`, `audit_root != "GENESIS"`, `admin` set to deployer.
5. If another error occurs, copy the **bottommost traceback/error line** together with the new transaction link for diagnosis.

**Update:** The user later provided a corrected v1.1 transaction `0x79b3144c72cfe26be5910307c31648ded8a365aba7e3b7ea15573c221a6ae003` showing **ACCEPTED** + GenVM **SUCCESS**. This deployment was executed by the user, not by this environment. Finalization and write-method tests remain unverified. See `DEPLOYMENT_RESULT.json`.
