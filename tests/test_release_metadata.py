"""Assert packaging consistency; not an on-chain receipt verifier."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deployment_info_and_source_checksum_are_consistent():
    info = json.loads((ROOT / 'verification/DEPLOYMENT_RESULT.json').read_text())
    source = ROOT / 'contracts/trace_sentry.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == info['included_v1_1_contract_sha256']
    assert info['observed_genvm_execution_result'] == 'SUCCESS'
    assert info['observed_transaction_status'] == 'ACCEPTED'
    assert info['finalization_independently_confirmed'] is False
    assert len(info['contract_address']) == 42
    assert len(info['deployment_transaction_hash']) == 66


def test_schema_points_at_original_deployable_source():
    schema = json.loads((ROOT / 'contract_schema.json').read_text())
    info = json.loads((ROOT / 'verification/DEPLOYMENT_RESULT.json').read_text())
    assert schema['entrypoint'] == 'contracts/trace_sentry.py'
    assert schema['contract_class'] == 'TraceSentry'
    assert schema['deployment']['contract_address'] == info['contract_address']
    assert schema['deployment']['transaction_hash'] == info['deployment_transaction_hash']
