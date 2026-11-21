import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# Load the real model against minimal fakes; these tests exercise protocol logic
# without importing Odoo, connecting to a database, or sending network requests.
class FakeField:
    def __call__(self, *args, **kwargs):
        return None

class FakeFields:
    def __getattr__(self, name):
        return FakeField()

odoo = types.ModuleType('odoo')
odoo._ = lambda s: s
odoo.fields = FakeFields()
odoo.models = types.SimpleNamespace(Model=object)
exceptions = types.ModuleType('odoo.exceptions')
exceptions.AccessError = type('AccessError', (Exception,), {})
exceptions.UserError = type('UserError', (Exception,), {})
requests = types.ModuleType('requests')
requests.RequestException = type('RequestException', (Exception,), {})
requests.Session = lambda: None
path = Path(__file__).resolve().parents[1] / 'models' / 'pos_request.py'
with patch.dict(sys.modules, {'odoo': odoo, 'odoo.exceptions': exceptions, 'requests': requests}):
    spec = importlib.util.spec_from_file_location('standalone_pos_request', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


class RequestRecord:
    _payload = module.PosRequest._payload
    action_submit = module.PosRequest.action_submit
    def __init__(self):
        self.id = 1
        self.reference = 'ref-stable'
        self.invoice_id = types.SimpleNamespace(id=42, state='posted', amount_residual=100, invalidate_recordset=lambda *args: None)
        self.partner_id = types.SimpleNamespace(id=9)
        self.invoice_number = 'INV/42'
        self.customer_name = 'Customer'
        self.amount_paise = 5000
        self.currency_id = types.SimpleNamespace(compare_amounts=lambda a, b: (a > b) - (a < b))
        self.instance = 'test-db'
        self.api_url = 'https://pos.example.test'
        self.api_key = 'odoo_test_key'
        self.state = 'draft'
        self.pos_request_id = 0
        self.qr_id = False
        self.env = types.SimpleNamespace(cr=types.SimpleNamespace(execute=lambda *args: None))
    def ensure_one(self): pass
    def _check_operator(self): pass
    def invalidate_recordset(self): pass
    def sudo(self): return self
    def write(self, values): self.__dict__.update(values)


class FakeSession:
    calls = []
    responses = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception): raise result
        return result


class ContractTests(unittest.TestCase):
    def setUp(self):
        FakeSession.calls = []
        FakeSession.responses = []
        self.rec = RequestRecord()

    def test_timeout_retry_preserves_full_payload_and_key(self):
        expected = {'instance': 'test-db', 'request_reference': 'ref-stable', 'invoice_id': '42',
                    'invoice_number': 'INV/42', 'customer_id': '9', 'customer_name': 'Customer',
                    'amount_paise': 5000, 'currency': 'INR'}
        response = types.SimpleNamespace(status_code=202, json=lambda: dict(expected, id=21, state='ready', collection={'razorpay_qr_id': 'qr_1'}))
        FakeSession.responses = [requests.RequestException(), response]
        with patch.object(requests, 'Session', FakeSession):
            self.rec.action_submit()
            self.assertEqual(self.rec.state, 'uncertain')
            self.rec.action_submit()
        self.assertEqual(self.rec.state, 'ready')
        self.assertEqual(self.rec.pos_request_id, 21)
        self.assertEqual(FakeSession.calls[0], FakeSession.calls[1])
        url, args = FakeSession.calls[0]
        self.assertEqual(url, 'https://pos.example.test/api/odoo/payment-requests')
        self.assertEqual(args['json'], expected)
        self.assertEqual(args['headers'], {'X-Odoo-Key': 'odoo_test_key'})
        self.assertFalse(args['allow_redirects'])

    def test_response_mismatch_does_not_accept_or_change_reference(self):
        wrong = dict(self.rec._payload(), id=21, state='ready', amount_paise=1, collection={'razorpay_qr_id': 'qr_1'})
        FakeSession.responses = [types.SimpleNamespace(status_code=202, json=lambda: wrong)]
        with patch.object(requests, 'Session', FakeSession):
            self.rec.action_submit()
        self.assertEqual(self.rec.state, 'uncertain')
        self.assertEqual(self.rec.reference, 'ref-stable')
        self.assertFalse(self.rec.pos_request_id)

    def test_http_errors_keep_original_reference(self):
        FakeSession.responses = [types.SimpleNamespace(status_code=409)]
        with patch.object(requests, 'Session', FakeSession):
            self.rec.action_submit()
        self.assertEqual(self.rec.state, 'uncertain')
        self.assertEqual(self.rec.reference, 'ref-stable')

if __name__ == '__main__': unittest.main()
