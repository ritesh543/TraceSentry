"""Deterministic host-side contract harness, NOT GenVM or real chain execution.

Imports the actual deployable contract file with mocked GenLayer primitives and
mock consensus; tests exercise real contract state transitions and authorization.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path
import pytest

ADMIN = '0x' + '1' * 40
ALICE = '0x' + '2' * 40
BOB = '0x' + '3' * 40
CAROL = '0x' + '4' * 40
MALLORY = '0x' + '5' * 40

SOURCE = ('Safety bulletin ID TRS-247 confirms the packaged product batch was '
          'exposed to serious temperature abuse during transit on 12 July 2026. '
          'Detailed independent inspection recorded compromised seals and unsafe '
          'conditions. The lots need evaluation and immediate containment.')
REBUTTAL = ('Independent retesting bulletin ID TRS-248 demonstrates that the '
            'reported temperature sensor was miscalibrated and the goods stayed '
            'inside validated safety limits. Multiple calibrated devices and signed '
            'laboratory certificates support the corrected measurements.')
ANCHOR = 'exposed to serious temperature abuse during transit'
REBUTTAL_ANCHOR = 'reported temperature sensor was miscalibrated'
SHA = 'ab' * 32


class UserError(Exception):
    pass


class Store(dict):
    """Mock GenVM's zero-initialized mapping without allowing TreeMap()."""
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, *args, **kwargs):
        raise AssertionError('unparameterized TreeMap() cannot initialize a typed storage slot')

    @classmethod
    def zero_storage(cls):
        value = dict.__new__(cls)
        dict.__init__(value)
        return value


class Array(list):
    """Mock GenVM's zero-initialized dynamic array without explicit constructor."""
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, *args, **kwargs):
        raise AssertionError('storage DynArray is already zero-initialized')

    @classmethod
    def zero_storage(cls):
        value = list.__new__(cls)
        list.__init__(value)
        return value


class MockContract:
    def __getattr__(self, name):
        declared_type = type(self).__annotations__.get(name)
        if declared_type in (Store, Array):
            value = declared_type.zero_storage()
            setattr(self, name, value)
            return value
        raise AttributeError(name)


class Return:
    def __init__(self, calldata):
        self.calldata = calldata


@pytest.fixture
def harness(monkeypatch):
    def passthrough(f):
        return f

    class Engine:
        def __init__(self):
            self.pages = {'https://evidence.example.org/primary': SOURCE,
                          'https://evidence.example.org/rebuttal': REBUTTAL}
            self.responses = []
            self.prompt_calls = 0
            self.web_calls = 0

        def render(self, url, mode='text'):
            self.web_calls += 1
            return self.pages[url]

        def prompt(self, prompt):
            self.prompt_calls += 1
            if self.responses:
                return json.dumps(self.responses.pop(0))
            if 'independently adjudicate a supply-chain safety appeal' in prompt:
                return json.dumps({'action': 'OVERTURN', 'severity': 0, 'anchor': REBUTTAL_ANCHOR,
                                   'rationale': 'The newer independent laboratory report invalidates the first allegation.'})
            return json.dumps({'decision': 'SUBSTANTIATED', 'severity': 3,
                               'anchor': ANCHOR, 'rationale': 'Evidence indicates a major product safety failure.'})

        def consensus(self, leader, validator):
            result = leader()
            if not validator(Return(result)):
                raise UserError('validator consensus rejected the leader')
            return result

    sdk = types.ModuleType('genlayer')
    engine = Engine()
    gl = types.SimpleNamespace(
        Contract=MockContract,
        message=types.SimpleNamespace(sender_address=ADMIN),
        message_raw={'datetime': '2026-11-18T06:00:00+00:00'},
        public=types.SimpleNamespace(view=passthrough, write=passthrough),
        vm=types.SimpleNamespace(UserError=UserError, Return=Return,
                                  run_nondet_unsafe=engine.consensus),
        nondet=types.SimpleNamespace(web=types.SimpleNamespace(render=engine.render), exec_prompt=engine.prompt),
    )
    sdk.gl = gl
    sdk.TreeMap = Store
    sdk.DynArray = Array
    sdk.Address = str
    sdk.u32 = int
    sdk.__all__ = ['gl', 'TreeMap', 'DynArray', 'Address', 'u32']
    monkeypatch.setitem(sys.modules, 'genlayer', sdk)
    contract_path = Path(__file__).resolve().parents[1] / 'contracts' / 'trace_sentry.py'
    spec = importlib.util.spec_from_file_location('tracesentry_under_test', contract_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    contract = module.TraceSentry()

    class Harness:
        pass

    Harness.contract = contract
    Harness.engine = engine
    Harness.gl = gl
    Harness.UserError = UserError

    class Harness(Harness):

        def user(self, addr):
            self.gl.message.sender_address = addr
            return self

        def enroll(self, addr, supplier=True, reporter=False):
            self.user(addr)
            self.contract.enroll('Supplier ' + addr[2:8], 'Manages inspected batches and traceable shipments')
            self.user(ADMIN)
            self.contract.configure_participant(addr, supplier, reporter, True)
            return self

        def lot(self, lid, parents=None, actor=ALICE):
            self.user(actor)
            self.contract.register_lot(lid, 'Precision product batch ' + lid,
                                       'SKU-' + lid, json.dumps(parents or []), SHA)
            return self

        def submit(self, origin='lot-a', actor=ALICE):
            self.user(actor)
            return self.contract.submit_case(origin, 'CONTAMINATION',
                       'Temperature breach and health hazard linked to exposed goods.',
                       'https://evidence.example.org/primary', SHA)

        def assess(self, cid, actor=CAROL):
            self.user(actor)
            self.contract.assess_case(cid)
            return self

        def drain(self, cid, size=32):
            self.user(CAROL)
            while self.contract.get_case(cid)['mode'] in ('SPREAD', 'CLEAR'):
                self.contract.process_case(cid, size)
            return self

        def challenge(self, cid, actor=ALICE):
            self.user(actor)
            return self.contract.challenge_case(cid, 'https://evidence.example.org/rebuttal', SHA,
                          'Laboratory measurements contradict the sensor alert and the recall request.')

    return Harness()


@pytest.fixture
def ready(harness):
    harness.enroll(ALICE).enroll(BOB).enroll(CAROL, supplier=False, reporter=True)
    harness.lot('lot-a')
    return harness
