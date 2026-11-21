"""Adversarial, invariant and state-machine tests using a mock GenLayer SDK."""
import hashlib
import json
import random

import pytest

from conftest import ADMIN, ALICE, BOB, CAROL, MALLORY, SHA, SOURCE, ANCHOR, REBUTTAL, REBUTTAL_ANCHOR
from test_contract import rejects


@pytest.mark.parametrize('batch', [1, 2, 3, 4, 7, 31, 32])
def test_deterministic_resume_and_idempotent_queue(batch, ready):
    ready.lot('child-one', ['lot-a']).lot('child-two', ['lot-a'])
    ready.lot('grandchild', ['child-one', 'child-two'])
    cid = ready.submit()
    ready.assess(cid).drain(cid, batch)
    case = ready.contract.get_case(cid)
    assert case['mode'] == 'DONE'
    assert case['cursor'] == len(case['queue']) == 4
    assert len(set(case['queue'])) == 4
    assert ready.contract.get_stats()['pending_jobs'] == 0


@pytest.mark.parametrize('seed', [7, 29, 103, 2026, 9182])
def test_random_dag_bfs_is_exact(seed, ready):
    rng = random.Random(seed)
    parents = {'lot-a': []}
    children = {'lot-a': []}
    names = ['lot-a']
    for i in range(1, 42):
        name = f'n-{i:03}'
        eligible = [p for p in names if len(children[p]) < ready.contract.MAX_CHILDREN]
        count = rng.randint(0, min(3, len(eligible)))
        new_parents = rng.sample(eligible, count)
        ready.lot(name, new_parents)
        parents[name] = new_parents
        children[name] = []
        for parent in new_parents:
            children[parent].append(name)
        names.append(name)

    expected = {'lot-a'}
    stack = ['lot-a']
    while stack:
        for child in children[stack.pop()]:
            if child not in expected:
                expected.add(child)
                stack.append(child)

    cid = ready.submit()
    ready.assess(cid).drain(cid, rng.randint(1, 32))
    case = ready.contract.get_case(cid)
    assert len(case['queue']) == len(expected)
    assert set(case['queue']) == expected
    for name in names:
        risk = ready.contract.get_lot_risk(name)
        assert risk['severity'] == (3 if name in expected else 0)

    ready.user(ADMIN)
    ready.contract.emergency_retract(cid, 'Documented false-positive requires complete reversal of prior safety marks.')
    ready.drain(cid, rng.randint(1, 32))
    assert ready.contract.get_stats()['pending_jobs'] == 0
    assert all(ready.contract.get_lot_risk(name)['case_ids'] == [] for name in names)


def test_independent_origin_alerts_merge_and_clear_without_cross_damage(ready):
    ready.lot('left').lot('right')
    ready.lot('join', ['left', 'right']).lot('leaf', ['join'])
    first = ready.submit('left')
    second = ready.submit('right')
    ready.assess(first).assess(second)
    ready.drain(first, 1).drain(second, 1)
    assert set(ready.contract.get_lot_risk('leaf')['case_ids']) == {first, second}
    ready.user(ADMIN)
    ready.contract.emergency_retract(first, 'Verified correction of the first independent incident assessment.')
    ready.drain(first, 2)
    assert ready.contract.get_lot_risk('leaf')['case_ids'] == [second]
    assert ready.contract.get_lot_risk('leaf')['severity'] == 3


def test_clear_workflow_keeps_unprocessed_descendants_flagged(ready):
    ready.lot('lot-b', ['lot-a']).lot('lot-c', ['lot-b'])
    cid = ready.submit()
    ready.assess(cid).drain(cid, 2)
    ready.user(ADMIN)
    ready.contract.emergency_retract(cid, 'Independent test results require correction of earlier safety determination.')
    assert all(ready.contract.get_lot_risk(lid)['severity'] == 3 for lid in ('lot-a','lot-b','lot-c'))
    ready.user(CAROL)
    response = ready.contract.process_case(cid, 1)
    assert response['mode'] == 'CLEAR'
    assert ready.contract.get_lot_risk('lot-a')['severity'] == 0
    assert ready.contract.get_lot_risk('lot-b')['severity'] == 3
    assert ready.contract.get_lot_risk('lot-c')['severity'] == 3
    ready.drain(cid, 1)
    assert all(ready.contract.get_lot_risk(lid)['severity'] == 0 for lid in ('lot-a','lot-b','lot-c'))


def test_pending_case_sees_children_created_before_adjudication(ready):
    cid = ready.submit()
    ready.lot('later-descendant', ['lot-a'])
    ready.assess(cid).drain(cid)
    assert ready.contract.get_lot_risk('later-descendant')['severity'] == 3


def test_dismissed_incident_does_not_block_lot_creation(ready):
    cid = ready.submit()
    insufficient = {'decision': 'INSUFFICIENT', 'severity': 0, 'anchor': '',
                    'rationale': 'The provided text does not establish the alleged issue.'}
    ready.engine.responses = [insufficient, insufficient]
    ready.assess(cid)
    ready.lot('new-after-dismissal', ['lot-a'])
    assert ready.contract.get_lot_risk('new-after-dismissal')['severity'] == 0


def test_pause_blocks_inflight_queue_and_resumes(ready):
    cid = ready.submit()
    ready.assess(cid)
    ready.user(ADMIN)
    ready.contract.set_paused(True)
    ready.user(CAROL)
    rejects(ready, 'system paused', ready.contract.process_case, cid, 1)
    assert ready.contract.get_stats()['pending_jobs'] == 1
    ready.user(ADMIN)
    ready.contract.set_paused(False)
    ready.drain(cid)
    assert ready.contract.get_stats()['pending_jobs'] == 0


def test_pause_does_not_block_admin_retraction_but_blocks_clear_processing(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    ready.user(ADMIN)
    ready.contract.set_paused(True)
    ready.contract.emergency_retract(cid, 'Official product-safety correction after independent batch verification.')
    assert ready.contract.get_case(cid)['mode'] == 'CLEAR'
    ready.user(CAROL)
    rejects(ready, 'system paused', ready.contract.process_case, cid, 1)
    ready.user(ADMIN)
    ready.contract.set_paused(False)
    ready.drain(cid)
    assert ready.contract.get_case(cid)['status'] == 'CLEARED'


def test_unauthorized_reporter_cannot_appeal(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    ready.user(MALLORY)
    rejects(ready, 'custodian / approved reporter', ready.contract.challenge_case,
            cid, 'https://evidence.example.org/rebuttal', SHA,
            'Independent laboratory inspection contradicts the previously published assessment.')
    assert ready.contract.get_stats()['challenges'] == 0


def test_upheld_appeal_retains_original_warning_and_can_not_reresolve(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    upheld = {'action': 'UPHOLD', 'severity': 3, 'anchor': ANCHOR,
              'rationale': 'The original documentation remains credible despite contrary allegations.'}
    ready.engine.responses = [upheld, upheld]
    ready.user(CAROL)
    ready.contract.resolve_challenge(aid)
    assert ready.contract.get_challenge(aid)['action'] == 'UPHOLD'
    assert ready.contract.get_lot_risk('lot-a')['severity'] == 3
    rejects(ready, 'challenge already resolved', ready.contract.resolve_challenge, aid)


@pytest.mark.parametrize('payload', [
    {'decision': 'SUBSTANTIATED', 'severity': 0, 'anchor': ANCHOR,
     'rationale': 'Severity zero is incompatible with substantiation.'},
    {'decision': 'INSUFFICIENT', 'severity': 1, 'anchor': '',
     'rationale': 'Insufficient decision must have severity zero.'},
    {'decision': 'SUBSTANTIATED', 'severity': True, 'anchor': ANCHOR,
     'rationale': 'A boolean is not a valid integer severity.'},
    {'decision': 'SUBSTANTIATED', 'severity': 7, 'anchor': ANCHOR,
     'rationale': 'Out-of-bounds high severity must be rejected.'},
    {'decision': 'UNSAFE', 'severity': 2, 'anchor': ANCHOR,
     'rationale': 'Unknown decision label must be rejected.'},
    {'decision': 'SUBSTANTIATED', 'severity': 2, 'anchor': 'invented evidence quote',
     'rationale': 'Ungrounded source quotation must be rejected.'},
    {'decision': 'INSUFFICIENT', 'severity': 0, 'anchor': 'invented evidence quote',
     'rationale': 'Even an optional quotation must be grounded.'},
    {'decision': 'SUBSTANTIATED', 'severity': 2, 'anchor': ANCHOR,
     'rationale': 'short'},
    {'decision': 'SUBSTANTIATED', 'severity': 2, 'anchor': 'x' * 181,
     'rationale': 'The source quotation is too long to accept.'},
])
def test_ai_assessment_rejects_bad_structured_decisions(payload, ready):
    cid = ready.submit()
    ready.engine.responses = [payload]
    ready.user(CAROL)
    with pytest.raises(ready.UserError, match='invalid source-grounded assessment'):
        ready.contract.assess_case(cid)
    assert ready.contract.get_case(cid)['status'] == 'PENDING'
    assert ready.contract.get_stats()['pending_jobs'] == 0


@pytest.mark.parametrize('case', ['invalid-type', 'bad-prompt', 'short-evidence'])
def test_non_deterministic_input_failure_is_not_silent(case, ready):
    cid = ready.submit()
    if case == 'invalid-type':
        ready.engine.responses = [{'decision':'SUBSTANTIATED','severity':'3',
                                   'anchor':ANCHOR,'rationale':'Severity is a string, not integer.'}]
    elif case == 'bad-prompt':
        ready.engine.responses = [{'unexpected': 'not an assessment'}]
    else:
        ready.engine.pages['https://evidence.example.org/primary'] = 'short'
    ready.user(CAROL)
    with pytest.raises(ready.UserError):
        ready.contract.assess_case(cid)
    assert ready.contract.get_case(cid)['status'] == 'PENDING'


def _assessment(severity, **overrides):
    payload = {
        'decision': 'SUBSTANTIATED' if severity else 'INSUFFICIENT',
        'severity': severity,
        'anchor': ANCHOR if severity else '',
        'rationale': 'The source was reviewed for product safety evidence.',
    }
    return payload | overrides


@pytest.mark.parametrize('leader_level,validator_level', [
    (leader, validator)
    for leader in range(4)
    for validator in range(4)
    if leader != validator
])
def test_severity_disagreement_leaves_case_and_lot_risk_unmodified(leader_level, validator_level, ready):
    ready.lot('downstream', ['lot-a'])
    cid = ready.submit()
    original = ready.contract.get_case(cid)
    stats = ready.contract.get_stats()
    ready.engine.responses = [_assessment(leader_level), _assessment(validator_level)]

    rejects(ready, 'consensus rejected', ready.assess, cid)

    assert ready.engine.prompt_calls == 2
    assert ready.contract.get_case(cid) == original
    assert ready.contract.get_stats() == stats
    assert not ready.contract.case_seen
    for lot_id in ('lot-a', 'downstream'):
        assert ready.contract.get_lot_risk(lot_id) == {
            'severity': 0, 'classification': 'CLEAR', 'case_ids': [],
        }


@pytest.mark.parametrize('level,classification', [
    (0, 'CLEAR'), (1, 'WATCH'), (2, 'RECALL'), (3, 'CRITICAL'),
])
def test_exact_severity_consensus_controls_origin_and_downstream_risk(level, classification, ready):
    ready.lot('downstream', ['lot-a'])
    cid = ready.submit()
    ready.engine.responses = [_assessment(level), _assessment(
        level, rationale='Independent review reached the same classification.'
    )]
    ready.assess(cid).drain(cid, size=1)

    case = ready.contract.get_case(cid)
    assert case['severity'] == level
    assert case['status'] == ('ACTIVE' if level else 'DISMISSED')
    assert case['mode'] == 'DONE'
    for lot_id in ('lot-a', 'downstream'):
        assert ready.contract.get_lot_risk(lot_id) == {
            'severity': level, 'classification': classification, 'case_ids': [cid] if level else [],
        }


def test_leader_quote_must_appear_in_the_snapshot_used_by_the_validator(ready, monkeypatch):
    cid = ready.submit()
    new_anchor = 'showed evidence of compromised packaging'
    revised = SOURCE.replace(ANCHOR, new_anchor)
    snapshots = iter([SOURCE, revised, SOURCE])
    monkeypatch.setattr(ready.gl.nondet.web, 'render', lambda url, mode: next(snapshots))
    ready.engine.responses = [_assessment(2), _assessment(2, anchor=new_anchor)]

    rejects(ready, 'consensus rejected', ready.assess, cid)

    assert ready.contract.get_case(cid)['status'] == 'PENDING'


@pytest.mark.parametrize('fields', [
    {'severity': True},
    {'rationale': ['explanation'] * 8},
    {'category': 'TRANSPORT'},
])
def test_validator_rejects_malformed_assessment_payload(fields, ready, monkeypatch):
    cid = ready.submit()
    ready.engine.responses = [_assessment(1), _assessment(1)]

    def mock_consensus(leader, validator):
        assert validator(ready.gl.vm.Return(leader() | fields)) is False
        raise ready.UserError('validator consensus rejected the leader')

    monkeypatch.setattr(ready.gl.vm, 'run_nondet_unsafe', mock_consensus)
    rejects(ready, 'consensus rejected', ready.assess, cid)
    assert ready.contract.get_case(cid)['status'] == 'PENDING'


@pytest.mark.parametrize('leader_level,validator_level', [(1, 2), (2, 1)])
def test_appeal_downgrade_requires_exact_new_severity(leader_level, validator_level, ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    pending = ready.contract.get_challenge(aid)
    stats = ready.contract.get_stats()
    downgrade = {'action': 'DOWNGRADE', 'anchor': REBUTTAL_ANCHOR,
                 'rationale': 'The rebuttal supports lowering the safety response.'}
    ready.engine.responses = [
        dict(downgrade, severity=leader_level),
        dict(downgrade, severity=validator_level),
    ]

    rejects(ready, 'consensus rejected', ready.contract.resolve_challenge, aid)

    assert ready.contract.get_challenge(aid) == pending
    assert ready.contract.get_stats() == stats
    assert ready.contract.get_lot_risk('lot-a')['classification'] == 'CRITICAL'


def test_appeal_uses_the_challengers_argument_and_fresh_evidence(ready, monkeypatch):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    prompts = []
    fetches_before = ready.engine.web_calls

    def capture(prompt):
        prompts.append(json.loads(prompt.split('\nInput JSON:\n', 1)[1]))
        return ready.engine.prompt(prompt)

    monkeypatch.setattr(ready.gl.nondet, 'exec_prompt', capture)
    ready.contract.resolve_challenge(aid)

    assert len(prompts) == 2
    for evidence in prompts:
        assert evidence['argument'] == ready.contract.get_challenge(aid)['argument']
        assert evidence['original_evidence'] == SOURCE
        assert evidence['rebuttal_evidence'] == REBUTTAL
    assert ready.engine.web_calls - fetches_before == 4


def test_appeal_invalid_downgrade_when_prior_watch_severity(ready):
    cid = ready.submit()
    watch = {'decision':'SUBSTANTIATED','severity':1,'anchor':ANCHOR,
             'rationale':'Credible evidence supports cautious ongoing observation.'}
    ready.engine.responses = [watch, watch]
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    lower = {'action':'DOWNGRADE','severity':1,'anchor':REBUTTAL_ANCHOR,
             'rationale':'Cannot downgrade a one-level watch to the same value.'}
    ready.engine.responses = [lower]
    ready.user(CAROL)
    rejects(ready, 'invalid appeal severity transition', ready.contract.resolve_challenge, aid)
    assert ready.contract.get_challenge(aid)['status'] == 'PENDING'


def test_appeal_anchor_not_in_either_document_is_rejected(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    invalid = {'action':'OVERTURN','severity':0,'anchor':'fictional independent report not on page',
               'rationale':'Alleged source excerpt cannot be found in provided evidence.'}
    ready.engine.responses = [invalid]
    ready.user(CAROL)
    rejects(ready, 'invalid appeal assessment', ready.contract.resolve_challenge, aid)


def test_appeal_too_short_rebuttal_is_rejected(ready):
    cid = ready.submit()
    ready.assess(cid).drain(cid)
    aid = ready.challenge(cid)
    ready.engine.pages['https://evidence.example.org/rebuttal'] = 'not enough'
    ready.user(CAROL)
    rejects(ready, 'appeal evidence too short', ready.contract.resolve_challenge, aid)


def test_exact_admin_role_assignment_requires_enrollment(ready):
    ready.user(ADMIN)
    rejects(ready, 'record does not exist', ready.contract.configure_participant,
            MALLORY, True, True, True)
    assert not ready.contract.participants.get(MALLORY)


def test_admin_proposal_rejects_same_address(ready):
    ready.user(ADMIN)
    rejects(ready, 'admin already set', ready.contract.propose_admin, ADMIN)


@pytest.mark.parametrize('bad', [
    'http://evidence.example.org/', 'https://localhost/foo',
    'https://10.0.0.1/x', 'https://172.16.1.1/route',
    'https://example.org:8443/file', 'https://user@example.org/',
    'https://[::1]/x', 'ftp://example.org/doc',
])
def test_public_evidence_host_validation(bad, ready):
    ready.user(ALICE)
    with pytest.raises(ready.UserError):
        ready.contract.submit_case('lot-a','OTHER',
          'Packaging failure presents an identifiable product hazard.',bad,SHA)


def test_audit_chain_pagination_and_snapshot(ready):
    for i in range(50):
        ready.lot('free-' + str(i))
    stats = ready.contract.get_stats()
    assert stats['audit_entries'] > 32
    events = []
    for start in range(0, stats['audit_entries'], 13):
        events.extend(ready.contract.get_audit(start, 13))
    assert len(events) == stats['audit_entries']
    previous = 'GENESIS'
    for seq, raw in enumerate(events, start=1):
        event = json.loads(raw)
        entry = event['record']
        assert entry['seq'] == seq and entry['previous'] == previous
        payload = json.dumps(entry, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        assert hashlib.sha256(payload.encode()).hexdigest() == event['hash']
        previous = event['hash']
    assert stats['audit_root'] == previous


def test_implicit_constructor_no_arguments_and_initial_audit(ready):
    stats = ready.contract.get_stats()
    assert stats['lots'] == 1
    first = json.loads(ready.contract.get_audit(0,1)[0])
    assert first['record']['event'] == 'DEPLOY'
    assert first['record']['data']['admin'] == ADMIN


def test_non_admin_cannot_modify_governance_after_role_approval(ready):
    ready.user(ALICE)
    rejects(ready, 'admin only', ready.contract.propose_admin, ALICE)
    rejects(ready, 'admin only', ready.contract.set_paused, True)
    rejects(ready, 'admin only', ready.contract.configure_participant, BOB, True, False, True)
