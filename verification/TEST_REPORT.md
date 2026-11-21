# TraceSentry v1.2 verification report

**Run date** 21 November 2026.  
**Base GitHub commit** `662713af1ccf7c14998d6daaa1a6af0865b63b4f`.  
**Source** `contracts/trace_sentry.py` with SHA-256 `eec9cdc4461cf6ac4c6e0c3b1a01e98da646d5312f0143e0051cb64cff8b0f5a`.

| Check | Result |
| --- | --- |
| Host tests with Python 3.12.14 and pytest 9.0.2 | **121 passed** |
| Python compilation and Bash script syntax | **Passed** |
| GenVM AST lint with genvm-linter 0.11.0 | **Passed** |
| Pinned GenLayer SDK schema validation | **Passed** |
| Packaged schema compared with SDK output | **Passed** for 12 writes, 8 views and the zero-argument constructor |
| v1.2 live StudioNet execution and consensus | Pending deployment |

## Consensus regressions

- The case tests cover all 16 pairs of valid severity levels. All 12 disagreements reject, including 2 vs 3 and 3 vs 2. The tests verify the pending case, the job counters, the audit root, and the lot risk after rejection.
- The four matching pairs produce the corresponding `CLEAR`, `WATCH`, `RECALL`, or `CRITICAL` result on the origin and downstream lots. The independent explanations may differ.
- Schema and source regressions exercise malformed payloads and a revised source page. The validator checks the proposed quote against the same snapshot it uses for independent assessment.
- Appeal tests verify exact downgrade severity, the use of the recorded argument, and both evidence fetches on each node.

The host suite mocks GenLayer storage, the web, LLM calls and consensus. The SDK check loads the declared runner and validates the contract schema. It reports an informational note about a newer runner. StudioNet tests cover real transaction execution, validator votes, and finality. [Live test plan](LIVE_TEST_PLAN.md)

The restored v1.1 Studio record documents the earlier constructor transaction. [Historical v1.1 record](DEPLOYMENT_RESULT.json) · [Machine-readable results](TEST_REPORT.json)
