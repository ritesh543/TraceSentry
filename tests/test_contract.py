import hashlib
import json
import pytest
from conftest import ADMIN, ALICE, BOB, CAROL, MALLORY, SHA, ANCHOR, REBUTTAL_ANCHOR


def rejects(h, message, fn, *a):
    with pytest.raises(h.UserError, match=message):
        fn(*a)


def test_owner_and_metadata(harness):
    s = harness.contract.get_stats()
    assert s['admin'] == ADMIN and s['lots'] == 0 and s['pending_jobs'] == 0
    assert s['audit_entries'] == 1


def test_unapproved_supplier_cannot_mint(harness):
    harness.user(MALLORY)
    rejects(harness, 'approved supplier', harness.contract.register_lot,
            'x', 'Product batch', 'SKU-1', '[]', SHA)


def test_enroll_then_admin_approve(harness):
    harness.user(ALICE)
    harness.contract.enroll('North Logistics', 'Distributes cold-chain medical devices')
    rejects(harness, 'already enrolled', harness.contract.enroll, 'New Logistics', 'Another descriptor')
    harness.user(MALLORY)
    rejects(harness, 'admin only', harness.contract.configure_participant, ALICE, True, False, True)
    harness.user(ADMIN)
    harness.contract.configure_participant(ALICE, True, False, True)
    assert harness.contract.get_participant(ALICE)['roles'] == ['SUPPLIER']


def test_lot_dag_parent_link_and_fan_in(ready):
    ready.lot('lot-b', ['lot-a']).lot('lot-c', ['lot-a']).lot('lot-d', ['lot-b','lot-c'])
    assert ready.contract.get_lot('lot-d')['parents'] == ['lot-b','lot-c']
    assert ready.contract.get_children('lot-a') == ['lot-b','lot-c']
    assert ready.contract.get_stats()['lots'] == 4


def test_no_unregistered_parents(ready):
    rejects(ready, 'record does not exist', ready.contract.register_lot,
            'child', 'Good batch', 'SKU', '["ghost"]', SHA)


def test_duplicate_lot(ready):
    ready.user(ALICE)
    rejects(ready, 'duplicate lot', ready.contract.register_lot,
            'lot-a', 'Good batch', 'SKU', '[]', SHA)


def test_cannot_create_self_cycle(ready):
    ready.user(ALICE)
    rejects(ready, 'self-dependency', ready.contract.register_lot,
            'lot-b', 'Good batch', 'SKU', '["lot-b"]', SHA)


def test_no_duplicate_parent_entries(ready):
    ready.user(ALICE)
    rejects(ready, 'duplicate parents', ready.contract.register_lot,
            'lot-b', 'Good batch', 'SKU', '["lot-a","lot-a"]', SHA)


def test_invalid_parent_json(ready):
    ready.user(ALICE)
    rejects(ready, 'parents must be JSON', ready.contract.register_lot,
            'lot-b', 'Good batch', 'SKU', 'not-json', SHA)


def test_invalid_manifest(ready):
    ready.user(ALICE)
    rejects(ready, 'manifest hash must be hex', ready.contract.register_lot,
            'lot-b', 'Good batch', 'SKU', '[]', 'z'*64)


def test_sender_owns_lot(ready):
    ready.lot('lot-b', ['lot-a'], actor=BOB)
    assert ready.contract.get_lot('lot-b')['custodian'] == BOB


def test_evidence_permissions(ready):
    ready.user(MALLORY)
    rejects(ready, 'lot custodian or approved', ready.contract.submit_case,
            'lot-a', 'OTHER', 'Compromised transport packaging causing exposure.',
            'https://evidence.example.org/primary', SHA)


def test_approved_reporter_can_submit(ready):
    cid = ready.submit(actor=CAROL)
    assert ready.contract.get_case(cid)['reporter'] == CAROL


def test_invalid_urls_blocked(ready):
    for value in ('http://evidence.example.org/bulletin', 'https://localhost.local/report',
                  'https://admin@evidence.example.org/path', 'https://192.168.1.1/report'):
        ready.user(ALICE)
        with pytest.raises(ready.UserError):
            ready.contract.submit_case('lot-a', 'OTHER', 'Compromised transport packaging causing exposure.', value, SHA)
    assert ready.contract.get_stats()['cases'] == 0


def test_invalid_evidence_hash_blocked(ready):
    ready.user(ALICE)
    rejects(ready, 'sha256', ready.contract.submit_case, 'lot-a', 'OTHER',
            'Compromised transport packaging causing exposure.',
            'https://evidence.example.org/primary', 'nope')


def test_assessment_independent_validator(ready):
    cid = ready.submit()
    ready.assess(cid)
    assert ready.engine.prompt_calls == 2
    assert ready.engine.web_calls >= 3
    assert ready.contract.get_case(cid)['severity'] == 3
    assert ready.contract.get_case(cid)['mode'] == 'SPREAD'


def test_no_consensus_on_safety_boundary_disagreement(ready):
    cid = ready.submit()
    ready.engine.responses = [
        {'decision': 'SUBSTANTIATED', 'severity': 3, 'anchor': ANCHOR, 'rationale':'Serious confirmed safety hazard.'},
        {'decision': 'SUBSTANTIATED', 'severity': 1, 'anchor': ANCHOR, 'rationale':'Only mild watch evidence observed.'}
    ]
    with pytest.raises(ready.UserError, match='consensus rejected'):
        ready.assess(cid)
    assert ready.contract.get_case(cid)['status'] == 'PENDING'


def test_invalid_leader_anchor_rejected(ready):
    cid = ready.submit()
    ready.engine.responses = [{'decision':'SUBSTANTIATED', 'severity':3,
                               'anchor':'invented fake quote from nowhere',
                               'rationale':'Fabricated incident source statement.'}]
    with pytest.raises(ready.UserError, match='source anchor not grounded'):
        ready.assess(cid)


def test_severity_zero_is_dismissed(ready):
    cid = ready.submit()
    enough = {'decision':'INSUFFICIENT', 'severity':0, 'anchor':'',
              'rationale':'There is inadequate documentary support for the claim.'}
    ready.engine.responses = [enough, enough]
    ready.assess(cid)
    assert ready.contract.get_case(cid)['status'] == 'DISMISSED'
    assert ready.contract.get_stats()['pending_jobs'] == 0
    assert ready.contract.get_lot_risk('lot-a')['classification'] == 'CLEAR'


def test_spread_branch_merge_deduplicates(ready):
    ready.lot('lot-b',['lot-a']).lot('lot-c',['lot-a']).lot('lot-d',['lot-b','lot-c'])
    cid = ready.submit()
    ready.assess(cid).drain(cid, 1)
    case = ready.contract.get_case(cid)
    assert len(case['queue']) == 4
    assert len(set(case['queue'])) == 4
    assert case['status'] == 'ACTIVE' and case['mode'] == 'DONE'
    assert ready.contract.get_stats()['pending_jobs'] == 0
    for lot in ('lot-a','lot-b','lot-c','lot-d'):
        risk = ready.contract.get_lot_risk(lot)
        assert risk['classification'] == 'CRITICAL' and risk['case_ids'] == [cid]


def test_overlapping_cases_keep_risk_after_one_retracted(ready):
    ready.lot('lot-b',['lot-a'])
    first = ready.submit()
    second = ready.submit()
    ready.assess(first).drain(first)
    ready.assess(second).drain(second)
    assert len(ready.contract.get_lot_risk('lot-b')['case_ids']) == 2
    ready.user(ADMIN)
    ready.contract.emergency_retract(first, 'Official correction to source after an independent inspection.')
    ready.drain(first)
    assert ready.contract.get_lot_risk('lot-b')['case_ids'] == [second]
    assert ready.contract.get_case(first)['status'] == 'CLEARED'


def test_registrations_frozen_during_propagation(ready):
    cid = ready.submit()
    ready.assess(cid)
    ready.user(ALICE)
    rejects(ready, 'settle propagation', ready.contract.register_lot,
            'lot-b', 'Another shipment', 'SKU2', '[]', SHA)
    ready.drain(cid)
    ready.user(ALICE)
    rejects(ready, 'cannot consume flagged parent', ready.contract.register_lot,
            'lot-b', 'Another shipment', 'SKU2', '["lot-a"]', SHA)


def test_pause_blocks_new_writes_but_risks_readable(ready):
    ready.user(ADMIN)
    ready.contract.set_paused(True)
    ready.user(ALICE)
    rejects(ready, 'system paused', ready.contract.register_lot,
            'lot-b', 'Another shipment', 'SKU2', '[]', SHA)
    assert ready.contract.get_lot_risk('lot-a')['severity'] == 0
    ready.user(ADMIN)
    ready.contract.set_paused(False)
    ready.lot('lot-b')


def test_admin_nomination_two_step(ready):
    ready.user(ADMIN)
    ready.contract.propose_admin(BOB)
    ready.user(ALICE)
    rejects(ready, 'not nominated', ready.contract.accept_admin)
    ready.user(BOB)
    ready.contract.accept_admin()
    assert ready.contract.get_stats()['admin'] == BOB
    ready.user(ADMIN)
    rejects(ready, 'admin only', ready.contract.set_paused, True)


def test_valid_challenge_and_full_cascade_retraction(ready):
    ready.lot('lot-b',['lot-a']).lot('lot-c',['lot-b'])
    cid = ready.submit()
    ready.assess(cid).drain(cid, 1)
    appeal = ready.challenge(cid)
    ready.user(CAROL)
    ready.contract.resolve_challenge(appeal)
    assert ready.contract.get_challenge(appeal)['action'] == 'OVERTURN'
    assert ready.contract.get_case(cid)['mode'] == 'CLEAR'
    ready.drain(cid, 1)
    assert ready.contract.get_case(cid)['status'] == 'CLEARED'
    for lot in ('lot-a','lot-b','lot-c'):
        assert ready.contract.get_lot_risk(lot)['classification'] == 'CLEAR'


def test_challenge_not_allowed_during_propagation(ready):
    cid = ready.submit()
    ready.assess(cid)
    ready.user(ALICE)
    rejects(ready, 'only fully processed', ready.contract.challenge_case,
            cid, 'https://evidence.example.org/rebuttal', SHA,
            'Confirmed independent retest disputes the initial safety bulletin.')


def test_one_challenge_per_case(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    ready.challenge(cid)
    ready.user(ALICE)
    rejects(ready, 'one on-chain challenge', ready.contract.challenge_case,
            cid, 'https://evidence.example.org/rebuttal', SHA,
            'Confirmed independent retest disputes the initial safety bulletin.')


def test_downgrade_keeps_historical_marks_with_lower_risk(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    lower = {'action':'DOWNGRADE','severity':1,'anchor':REBUTTAL_ANCHOR,
             'rationale':'New testing suggests only a monitoring-level remaining risk.'}
    ready.engine.responses = [lower, lower]
    ready.user(CAROL)
    ready.contract.resolve_challenge(aid)
    assert ready.contract.get_case(cid)['severity'] == 1
    assert ready.contract.get_lot_risk('lot-a')['classification'] == 'WATCH'


def test_validator_rejects_appeal_disagreement(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    ready.engine.responses = [
      {'action':'OVERTURN', 'severity':0, 'anchor':REBUTTAL_ANCHOR, 'rationale':'Correction completely invalidates alarm.'},
      {'action':'UPHOLD', 'severity':3, 'anchor':ANCHOR, 'rationale':'Original incident remains fully substantiated.'}
    ]
    ready.user(CAROL)
    rejects(ready, 'consensus rejected', ready.contract.resolve_challenge, aid)
    assert ready.contract.get_challenge(aid)['status'] == 'PENDING'


def test_admin_emergency_retract_requires_complete_job(ready):
    cid = ready.submit()
    ready.assess(cid)
    ready.user(ADMIN)
    rejects(ready, 'propagation must finish', ready.contract.emergency_retract,
            cid, 'Administrative correction after independent evidence verification.')


def test_no_double_clear(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    ready.user(ADMIN)
    ready.contract.emergency_retract(cid, 'Documented mistake and data correction require retraction.')
    ready.drain(cid)
    ready.user(ADMIN)
    rejects(ready, 'propagation must finish', ready.contract.emergency_retract,
            cid, 'Documented mistake and data correction require retraction.')


def test_batch_boundaries(ready):
    cid = ready.submit()
    ready.assess(cid)
    ready.user(CAROL)
    for batch in (0, 33):
        rejects(ready, 'batch must be 1..32', ready.contract.process_case, cid, batch)
    assert ready.contract.process_case(cid, 1)['mode'] == 'DONE'
    rejects(ready, 'no pending propagation', ready.contract.process_case, cid, 1)


def test_huge_linear_graph_incremental_batches(ready):
    previous = 'lot-a'
    for i in range(1, 81):
        current = f'lot-{i:03d}'
        ready.lot(current, [previous])
        previous = current
    cid = ready.submit()
    ready.assess(cid).drain(cid, 7)
    assert len(ready.contract.get_case(cid)['queue']) == 81
    assert ready.contract.get_lot_risk(previous)['severity'] == 3
    ready.user(ADMIN)
    ready.contract.emergency_retract(cid, 'Independent evidence correction requires all descendants to be released.')
    ready.drain(cid, 13)
    assert ready.contract.get_lot_risk(previous)['severity'] == 0


def test_multiple_cascades_are_isolated(ready):
    ready.lot('lot-b',['lot-a']).lot('lot-c')
    a = ready.submit('lot-a')
    b = ready.submit('lot-c')
    ready.assess(a).assess(b)
    assert ready.contract.get_stats()['pending_jobs'] == 2
    ready.drain(a).drain(b)
    assert ready.contract.get_lot_risk('lot-b')['case_ids'] == [a]
    assert ready.contract.get_lot_risk('lot-c')['case_ids'] == [b]


def test_audit_hash_link_chain(ready):
    ready.lot('lot-b')
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    previous = 'GENESIS'
    entries = ready.contract.get_audit(0, 32)
    for item in entries:
        obj = json.loads(item)
        record = obj['record']
        assert record['previous'] == previous
        encoded = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        assert hashlib.sha256(encoded.encode()).hexdigest() == obj['hash']
        previous = obj['hash']
    assert ready.contract.get_stats()['audit_root'] == previous


def test_read_audit_pagination(ready):
    assert len(ready.contract.get_audit(0,1)) == 1
    rejects(ready,'audit page',ready.contract.get_audit,0,33)


def test_many_child_cap(ready):
    for idx in range(24):
        ready.lot('kid-' + str(idx), ['lot-a'])
    ready.user(ALICE)
    rejects(ready, 'parent fanout', ready.contract.register_lot,
            'overflow', 'Product batch extra', 'SKU', '["lot-a"]', SHA)


def test_hard_limits_are_configured(ready):
    assert ready.contract.MAX_LOTS == 512
    assert ready.contract.MAX_CASES == 128
    assert ready.contract.MAX_BATCH == 32


def test_revocation_of_supplier_role_blocks_future_lots(ready):
    ready.user(ADMIN)
    ready.contract.configure_participant(ALICE, True, False, False)
    ready.user(ALICE)
    rejects(ready, 'approved supplier', ready.contract.register_lot,
            'lot-b', 'Product batch', 'SKU', '[]', SHA)


def test_exhaustion_of_per_lot_submissions(ready):
    for _ in range(12):
        ready.submit()
    ready.user(ALICE)
    rejects(ready, 'case submission capacity', ready.contract.submit_case,
            'lot-a', 'OTHER', 'Unsafe handling caused contamination in the batch.',
            'https://evidence.example.org/primary', SHA)


def test_missing_lot_error(ready):
    rejects(ready, 'record does not exist', ready.contract.get_lot_risk, 'unknown')


def test_role_management_no_collateral_access(ready):
    ready.user(MALLORY)
    rejects(ready, 'admin only', ready.contract.set_paused, True)
    rejects(ready, 'admin only', ready.contract.emergency_retract,
            'case-0001', 'Premature emergency recall cancellation request.')


def test_validator_evidence_web_rescanned(ready):
    cid = ready.submit()
    ready.assess(cid)
    assert ready.engine.web_calls >= 3


def test_duplicate_assessment_rejected(ready):
    cid = ready.submit()
    ready.assess(cid)
    rejects(ready, 'case not pending', ready.contract.assess_case, cid)


def test_invalid_ids_blocked(ready):
    ready.user(ALICE)
    rejects(ready, 'id must be', ready.contract.register_lot,
            '../bad', 'Product batch', 'SKU', '[]', SHA)


def test_constructor_uses_implicit_typed_storage_zero_initialization(harness):
    """Regression: Studio deployment failed when __init__ used TreeMap()."""
    from conftest import Store, Array
    c = harness.contract
    for name in ('participants', 'lots', 'children', 'cases',
                 'challenges', 'lot_alerts', 'case_seen'):
        assert type(getattr(c, name)) is Store
        assert not getattr(c, name)
    assert type(c.audit) is Array
    assert len(c.audit) == 1  # DEPLOY audit initialized through append
    assert c.get_stats()['audit_entries'] == 1


def test_unparameterized_storage_allocation_is_rejected_by_mock():
    """Guard against mock tests hiding a GenVM storage-descriptor mismatch."""
    from conftest import Store, Array
    with pytest.raises(AssertionError, match='TreeMap'):
        Store()
    with pytest.raises(AssertionError, match='DynArray'):
        Array()
