# Deployment guide: GenLayer StudioNet

## Existing successful Studio deployment (v1.1)

The user provided Studio screenshots showing `ACCEPTED`, consensus `Accepted`, GenVM `SUCCESS`, result `Return`, and no stderr on the corrected v1.1 deployment. This **does not** prove `FINALIZED` or runtime behavior of other methods.

- Contract: `0x1C4C17d9A11531D7c27a3B65B24732A61E789D38`
- Transaction: `0x79b3144c72cfe26be5910307c31648ded8a365aba7e3b7ea15573c221a6ae003`
- Network: StudioNet (`61999`)
- Evidence: `verification/DEPLOYMENT_RESULT.json`

No new deployment is required to run the read-only checks. Run `./scripts/smoke_deployed_readonly.sh` on a machine with GenLayer CLI and internet access.


## Important: earlier deployment failed in GenVM

The original contract version's transaction `0xf83d3faba96fcaef72b70d65763232e705411b23b86b29dc746f41b350850c36` was **FINALIZED but did not deploy successfully**: `GenVM Execution Result: ERROR`, `Contract Error`, `exit_code 1` due to `TreeMap()` type-descriptor mismatch. This ZIP contains the **corrected constructor**. A corrected v1.1 deployment has already been accepted; use the existing address above. Do not redeploy unless intentionally creating a separate contract instance. Never use the old address as deployment proof. See `verification/FAILED_STUDIO_TRANSACTION.md`.

## Prerequisites

- Node.js 18+ and npm.
- Python 3.12+ if running tests/linter.
- Working public network access to GenLayer StudioNet.
- An **empty disposable test wallet**. Do not reuse production seeds or send private keys to other people.
- Test GEN if the selected network/transaction configuration requires it.

## 1. Inspect code, tests and limitations

```bash
unzip TraceSentry_GenLayer.zip
cd TraceSentry
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -v
python3 -m py_compile contracts/trace_sentry.py
python3 -m pip install -r requirements-genlayer.txt
genvm-lint check contracts/trace_sentry.py
```

Run real GenLayer direct tests/integration tests before using non-test stakes. The bundled host-side tests use a **handwritten mock runner**, not the GenVM.

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

Then:

1. Switch to supplier wallet, call `enroll("Demo Supply Co", "Test batch provenance operator")`.
2. Switch to deployer, call `configure_participant(<supplier address>, true, false, true)`.
3. Switch to supplier, call `register_lot("demo-root", "Demo root batch", "DEMO", "[]", "<64 hex>")`.
4. Verify `get_lot("demo-root")` and `get_lot_risk("demo-root")`.
5. Submit incident only using **a genuine public evidence URL**; invoke `assess_case("case-0001")`. The LLM may correctly dismiss an unsupported allegation.
6. If active, call `process_case("case-0001", 32)` until the stored mode is `DONE` and inspect descendant risk.
7. For live claims, test the appeal process with independently verifiable rebuttal evidence.

Capture real call outcomes, transactions and finality. A network explorer record is stronger evidence than a local test report.

## 7. Publish proof

For **future/new deployments**, record fresh values rather than overwriting the existing v1.1 evidence:

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
