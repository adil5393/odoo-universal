from unittest.mock import patch

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosRequest(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.inr = cls.env.ref('base.INR')
        cls.inr.active = True
        cls.company.currency_id = cls.inr
        cls.bank = cls.company_data['default_journal_bank']
        cls.company.write({'pos_qr_url': 'https://pos.example.test', 'pos_qr_instance': 'test-db',
                           'pos_qr_api_key': 'odoo_test_key', 'pos_qr_journal_id': cls.bank.id})
        cls.invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice', 'partner_id': cls.partner_a.id, 'currency_id': cls.inr.id,
            'invoice_line_ids': [Command.create({'name': 'Test', 'quantity': 1, 'price_unit': 100,
                'account_id': cls.company_data['default_account_revenue'].id, 'tax_ids': [Command.clear()]})],
        })
        cls.invoice.action_post()

    def make_request(self, amount=40):
        wizard = self.env['account.payment.register'].with_company(self.company).with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({'amount': amount, 'currency_id': self.inr.id})
        action = wizard.action_create_pos_qr()
        return self.env['universal.pos.request'].sudo().browse(action['res_id'])

    def event(self, rec):
        payload = rec._payload()
        payload.pop('customer_name')
        return dict(payload, event='payment.captured', event_id='evt_1', razorpay_qr_id='qr_1', razorpay_payment_id='pay_1')

    def test_partial_capture_and_duplicate(self):
        rec = self.make_request()
        self.assertEqual(rec.amount_paise, 4000)
        self.assertEqual(self.invoice.amount_residual, 100)
        rec._apply_capture(self.event(rec))
        self.assertEqual(rec.state, 'paid')
        self.assertEqual(rec.payment_id.state, 'posted')
        self.assertEqual(self.invoice.amount_residual, 60)
        payment = rec.payment_id
        rec._apply_capture(self.event(rec))
        self.assertEqual(rec.payment_id, payment)
        with self.assertRaises(ValueError):
            rec._apply_capture(dict(self.event(rec), event_id='evt_other'))

    def test_full_capture(self):
        rec = self.make_request(100)
        rec._apply_capture(self.event(rec))
        self.assertEqual(self.invoice.amount_residual, 0)
        self.assertEqual(rec.payment_id.journal_id, self.bank)

    def test_reservation_and_invalid_callback(self):
        rec = self.make_request(60)
        with self.assertRaises(UserError):
            self.make_request(41)
        for field, wrong in [('invoice_id', '999'), ('customer_id', '999'), ('currency', 'USD'),
                             ('amount_paise', 5999), ('instance', 'other')]:
            with self.assertRaises(ValueError):
                rec._apply_capture(dict(self.event(rec), **{field: wrong}))
        self.assertFalse(rec.payment_id)
        self.assertEqual(self.invoice.amount_residual, 100)

    def test_payment_and_event_cannot_be_reused_across_requests(self):
        first = self.make_request(40)
        second = self.make_request(40)
        first._apply_capture(self.event(first))
        for event in (dict(self.event(second), event_id='other'),
                      dict(self.event(second), razorpay_payment_id='other')):
            with self.assertRaises(ValueError):
                second._apply_capture(event)
        self.assertFalse(second.payment_id)
        self.assertEqual(self.invoice.amount_residual, 60)

    def test_uncertain_retry_uses_same_payload_and_reference(self):
        rec = self.make_request()
        expected = rec._payload()
        class Response:
            status_code = 202
            def json(self):
                return dict(expected, id=42, state='ready', collection={'razorpay_qr_id': 'qr_1'})
        with patch('odoo.addons.universal_pos_qr.models.pos_request.requests.Session') as session:
            session.return_value.__enter__.return_value.post.side_effect = [__import__('requests').Timeout(), Response()]
            rec.action_submit()
            self.assertEqual(rec.state, 'uncertain')
            rec.action_submit()
            self.assertEqual(rec.state, 'ready')
            calls = session.return_value.__enter__.return_value.post.call_args_list
            self.assertEqual(calls[0].kwargs['json'], calls[1].kwargs['json'])
            self.assertEqual(calls[0].kwargs['json'], expected)
            self.assertEqual(rec.pos_request_id, 42)
