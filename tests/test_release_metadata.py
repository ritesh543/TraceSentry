"""Assert packaging consistency; not an on-chain receipt verifier."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_pins_the_current_source():
    info = json.loads((ROOT / 'deployment_info.json').read_text())
    source = ROOT / info['source_file']
    assert source == ROOT / 'contracts' / 'trace_sentry.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == info['source_sha256']


def test_schema_and_release_metadata_agree_on_deployment():
    schema = json.loads((ROOT / 'contract_schema.json').read_text())
    info = json.loads((ROOT / 'deployment_info.json').read_text())
    assert schema['entrypoint'] == info['source_file']
    assert schema['contract_class'] == 'TraceSentry'
    assert schema['release_version'] == info['version']
    assert schema['deployment']['status'] == info['deployment_status']
    assert schema['deployment']['included_source_sha256'] == info['source_sha256']
    assert schema['deployment']['contract_address'] == info['contract_address']
    assert schema['deployment']['transaction_hash'] == info['transaction_hash']
    assert schema['deployed'] == bool(info['contract_address'] and info['transaction_hash'])


def test_v1_1_studio_record_is_preserved_as_historical_evidence():
    current = json.loads((ROOT / 'deployment_info.json').read_text())
    historical = json.loads((ROOT / current['historical_v1_1_verification']).read_text())
    assert historical['release'] == 'v1.1-studio-deployed-package'
    assert historical['included_v1_1_contract_sha256'] == 'ecb6407eed8ac0f2a24e08f49d0e52d399e830d479a94a5f1e1d6220e7a2d2ea'
    assert historical['observed_genvm_execution_result'] == 'SUCCESS'
    assert historical['observed_transaction_status'] == 'ACCEPTED'
    assert historical['finalization_independently_confirmed'] is False
    assert current['source_sha256'] != historical['included_v1_1_contract_sha256']
    assert current['contract_address'] != historical['contract_address']
    assert current['transaction_hash'] != historical['deployment_transaction_hash']
