# GenLayer StudioNet deployment guide

## TraceSentry v1.2

Deploy `contracts/trace_sentry.py` on stable StudioNet (chain ID 61999) for the exact severity consensus fix. The [release metadata](../deployment_info.json) records the v1.2 source hash and deployment status.

The v1.1 Studio receipt and the diagnosis of the earlier constructor issue are available for reference. [v1.1 receipt evidence](../verification/DEPLOYMENT_RESULT.json) · [v1.0 constructor diagnosis](../verification/FAILED_STUDIO_TRANSACTION.md)

## Prerequisites

- Node.js 18+ and npm.
- Python 3.12+ if running tests/linter.
- Working public network access to GenLayer StudioNet.
- An **empty disposable test wallet**. Do not reuse production seeds or send private keys to other people.
- Test GEN if the selected network/transaction configuration requires it.

## 1. Inspect code, tests and limitations

```bash
unzip TraceSentry_v1.2_ConsensusFix.zip
cd TraceSentry
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -v
python3 -m py_compile contracts/trace_sentry.py
python3 scripts/verify_bundle.py
python3 -m pip install -r requirements-genlayer.txt
genvm-lint check contracts/trace_sentry.py
```

The bundled host tests run with mocked GenLayer primitives. The SDK check loads the pinned contract interface. For on-chain method execution, use the live test plan below.

## 2. Install and select stable Studionet

```bash
npm install -g genlayer
genlayer --version
genlayer network set studionet
genlayer network info
```

Check `network info` shows the expected **stable StudioNet**, **chain ID 61999**. Do not confuse it with the experimental **studio-dev** (61997) or localnet (61127). Network presets and commands may change; inspect the exact version installed.

## 3. Select a test wallet and faucet

Use your installed CLI's account management / unlock instructions (see `genlayer account --help`) or the Studio account interface to generate/select a **new disposable account**. Copy only its *public address* into the faucet. **Never publish the seed phrase, raw private key, or wallet recovery backup.** Fund with test GEN if needed. Inspect the wallet and chain before signing.

## 4. Deploy with CLI

```bash
# From this repository root:
./scripts/deploy_studionet.sh

# Equivalent direct command:
genlayer deploy --contract contracts/trace_sentry.py
```

There are **no constructor arguments**. The deployer is the initial administrator. The shell helper prints network details and asks for explicit confirmation; you should read the displayed chain/fees first. If the CLI reports a transaction ID but stalls, **inspect the existing transaction** before attempting another deployment to avoid duplicates.

## 5. Deploy using hosted GenLayer Studio instead

1. Visit https://studio.genlayer.com/.
2. Open **Contracts** → **Add From File**.
3. Upload `contracts/trace_sentry.py` (single standalone file).
4. Choose **Run and Debug**; verify no parameters are requested in the constructor.
5. Choose the **deployer/test account** and click **Deploy**.
6. Inspect execution logs, transaction outcome, contract address, and finality status. Read `get_stats()`.

See official instructions: https://docs.genlayer.com/developers/intelligent-contracts/tools/genlayer-studio/deploying-contract

## 6. On-chain smoke test

From deployer wallet, confirm `get_stats()` reports `lots=0`, `cases=0`, `pending_jobs=0`, `audit_entries=1` and the deployer as admin.

The CLI helper takes the new contract address and performs read-only calls.

```bash
./scripts/smoke_deployed_readonly.sh "$ADDR"
```

Then:

1. Switch to supplier wallet, call `enroll("Demo Supply Co", "Test batch provenance operator")`.
2. Switch to deployer, call `configure_participant(<supplier address>, true, false, true)`.
3. Switch to supplier, call `register_lot("demo-root", "Demo root batch", "DEMO", "[]", "<64 hex>")`.
4. Verify `get_lot("demo-root")` and `get_lot_risk("demo-root")`.
5. Submit incident only using **a genuine public evidence URL**; invoke `assess_case("case-0001")`. The LLM may correctly dismiss an unsupported allegation.
6. If active, call `process_case("case-0001", 32)` until the stored mode is `DONE` and inspect descendant risk.
7. For live claims, test the appeal process with independently verifiable rebuttal evidence.

Capture the call outcomes, transaction receipts, and finality status. [Live test plan](../verification/LIVE_TEST_PLAN.md)

## 7. Publish proof

Record the v1.2 receipt and its source hash in `deployment_info.json` and the deployment section of `contract_schema.json` after verifying the new transaction.

```json
{
  "network": "studionet",
  "chain_id": 61999,
  "contract_address": "<actual address after deployment>",
  "transaction_hash": "<actual tx hash>",
  "finality": "<verified actual outcome>",
  "deployed_at": "<UTC time>",
  "deployer_address": "<public test address>"
}
```

Do not create a fake proof file with fabricated addresses or hashes.
