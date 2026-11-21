import json
from urllib.parse import urlsplit

import requests

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class PosRequest(models.Model):
    _name = 'universal.pos.request'
    _description = 'POS QR payment request'
    _order = 'id desc'
    _check_company_auto = True

    reference = fields.Char(required=True, readonly=True, index=True, copy=False)
    invoice_id = fields.Many2one('account.move', required=True, readonly=True, ondelete='restrict', check_company=True)
    invoice_number = fields.Char(required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', required=True, readonly=True, ondelete='restrict')
    customer_name = fields.Char(required=True, readonly=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, ondelete='restrict')
    currency_id = fields.Many2one('res.currency', required=True, readonly=True, ondelete='restrict')
    amount_paise = fields.Integer(required=True, readonly=True)
    outstanding_paise = fields.Integer(required=True, readonly=True)
    instance = fields.Char(required=True, readonly=True)
    api_url = fields.Char(required=True, readonly=True, groups='base.group_system')
    api_key = fields.Char(required=True, readonly=True, groups='base.group_system')
    journal_id = fields.Many2one('account.journal', required=True, readonly=True, ondelete='restrict', check_company=True)
    requested_by_id = fields.Many2one('res.users', required=True, readonly=True)
    pos_request_id = fields.Integer(readonly=True, copy=False)
    qr_id = fields.Char(readonly=True, copy=False)
    state = fields.Selection([('draft', 'Prepared'), ('uncertain', 'Submission uncertain'),
        ('creating', 'Creating'), ('ready', 'Ready'), ('ambiguous', 'POS outcome ambiguous'),
        ('paid', 'Paid'), ('cancelled', 'Cancelled before submission')], default='draft', required=True, readonly=True)
    last_error = fields.Char(readonly=True)
    payment_id = fields.Many2one('account.payment', readonly=True, ondelete='restrict', check_company=True)
    razorpay_payment_id = fields.Char(readonly=True, copy=False, index=True)
    event_id = fields.Char(readonly=True, copy=False, index=True)

    _sql_constraints = [
        ('pos_reference_unique', 'unique(reference)', 'The request reference must be unique.'),
        ('pos_payment_unique', 'unique(razorpay_payment_id)', 'This Razorpay payment is already recorded.'),
        ('pos_event_unique', 'unique(event_id)', 'This callback event is already recorded.'),
        ('pos_amount_positive', 'CHECK(amount_paise >= 100 AND amount_paise <= 100000000)', 'Invalid amount.'),
    ]

    def _payload(self):
        self.ensure_one()
        return {'instance': self.instance, 'request_reference': self.reference,
                'invoice_id': str(self.invoice_id.id), 'invoice_number': self.invoice_number,
                'customer_id': str(self.partner_id.id), 'customer_name': self.customer_name,
                'amount_paise': self.amount_paise, 'currency': 'INR'}

    def _check_operator(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        if not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_('Only accounting users may operate POS requests.'))

    def action_submit(self):
        self._check_operator()
        self.env.cr.execute('SELECT id FROM universal_pos_request WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        rec = self.sudo()
        if rec.state not in ('draft', 'uncertain', 'creating', 'ready', 'ambiguous'):
            raise UserError(_('This request cannot be submitted.'))
        url = urlsplit(rec.api_url)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise UserError(_('The POS base URL must be an HTTPS URL without credentials, query or fragment.'))
        rec.env.cr.execute('SELECT id FROM account_move WHERE id = %s FOR UPDATE', [rec.invoice_id.id])
        rec.invoice_id.invalidate_recordset(['amount_residual', 'state'])
        if rec.invoice_id.state != 'posted' or rec.currency_id.compare_amounts(rec.invoice_id.amount_residual, rec.amount_paise / 100) < 0:
            raise UserError(_('The invoice no longer has sufficient outstanding balance. Investigate this request before proceeding.'))
        payload = rec._payload()
        # The record is created in the preceding wizard transaction; this action runs separately.
        try:
            with requests.Session() as session:
                session.trust_env = False
                response = session.post(rec.api_url.rstrip('/') + '/api/odoo/payment-requests',
                    json=payload, headers={'X-Odoo-Key': rec.api_key}, timeout=(5, 20), allow_redirects=False)
            if response.status_code != 202:
                rec.write({'state': 'uncertain', 'last_error': _('POS returned HTTP %s. Retry this same request or investigate.') % response.status_code})
                return True
            data = response.json()
            if not isinstance(data, dict) or any(data.get(k) != v for k, v in payload.items()):
                raise ValueError('Response does not match the request')
            if type(data.get('id')) is not int or data['id'] <= 0 or data.get('state') not in ('creating', 'ready', 'ambiguous'):
                raise ValueError('Invalid response identity or state')
            if rec.pos_request_id and rec.pos_request_id != data['id']:
                raise ValueError('Changed POS request ID')
            collection = data.get('collection')
            qr_id = collection.get('razorpay_qr_id') if isinstance(collection, dict) else False
            if data['state'] == 'ready' and (not isinstance(qr_id, str) or not qr_id):
                raise ValueError('Missing QR ID')
            if rec.qr_id and qr_id and rec.qr_id != qr_id:
                raise ValueError('Changed QR ID')
            rec.write({'pos_request_id': data['id'], 'state': data['state'], 'qr_id': qr_id or rec.qr_id,
                       'last_error': _('Investigate this request at the POS before taking further action.') if data['state'] in ('creating', 'ambiguous') else False})
        except (requests.RequestException, ValueError, TypeError):
            rec.write({'state': 'uncertain', 'last_error': _('The POS response is uncertain. Retry only this same request reference.')})
        return True

    def _apply_capture(self, data):
        self.ensure_one()
        self.env.cr.execute('SELECT id FROM universal_pos_request WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        expected = self._payload()
        for field in ('instance', 'request_reference', 'invoice_id', 'invoice_number', 'customer_id', 'amount_paise', 'currency'):
            if data.get(field) != expected[field] or (field == 'amount_paise' and type(data.get(field)) is not int):
                raise ValueError('Callback does not match request')
        if data.get('event') != 'payment.captured' or any(not isinstance(data.get(k), str) or not data[k] for k in ('event_id', 'razorpay_qr_id', 'razorpay_payment_id')):
            raise ValueError('Invalid callback')
        if self.qr_id and self.qr_id != data['razorpay_qr_id']:
            raise ValueError('QR mismatch')
        if self.state == 'paid':
            if self.event_id == data['event_id'] and self.razorpay_payment_id == data['razorpay_payment_id'] and self.qr_id == data['razorpay_qr_id'] and self.payment_id.state == 'posted':
                return
            raise ValueError('Conflicting callback')
        if self.state not in ('draft', 'uncertain', 'creating', 'ready', 'ambiguous'):
            raise ValueError('Request is not payable')
        if self.search_count(['|', ('event_id', '=', data['event_id']), ('razorpay_payment_id', '=', data['razorpay_payment_id'])]):
            raise ValueError('Event or payment already used')
        invoice = self.invoice_id
        self.env.cr.execute('SELECT id FROM account_move WHERE id = %s FOR UPDATE', [invoice.id])
        invoice.invalidate_recordset()
        if (invoice.state != 'posted' or invoice.move_type != 'out_invoice' or invoice.company_id != self.company_id
                or invoice.partner_id != self.partner_id or invoice.currency_id != self.currency_id
                or invoice.currency_id.name != 'INR' or invoice.name != self.invoice_number
                or invoice.currency_id.compare_amounts(invoice.amount_residual, self.amount_paise / 100) < 0):
            raise ValueError('Invoice no longer matches or balance is insufficient')
        journal = self.journal_id
        if journal.type != 'bank' or journal.company_id != self.company_id:
            raise ValueError('Invalid POS bank journal')
        method = journal._get_available_payment_method_lines('inbound').filtered(lambda line: line.code == 'manual')[:1]
        if not method:
            raise ValueError('The POS bank journal requires an inbound manual payment method')
        wizard = self.env['account.payment.register'].with_company(self.company_id).with_context(
            active_model='account.move', active_ids=invoice.ids).create({
                'journal_id': journal.id, 'payment_method_line_id': method.id,
                'amount': self.amount_paise / 100, 'currency_id': self.currency_id.id, 'group_payment': True,
                'payment_date': fields.Date.context_today(self), 'payment_difference_handling': 'open',
                'communication': data['razorpay_payment_id'],
            })
        before = invoice.amount_residual
        payments = wizard._create_payments()
        invoice.invalidate_recordset(['amount_residual'])
        if invoice.currency_id.compare_amounts(before - invoice.amount_residual, self.amount_paise / 100):
            raise ValueError('Payment did not reconcile the expected amount')
        if len(payments) != 1 or payments.state != 'posted':
            raise ValueError('Payment posting failed')
        self.write({'state': 'paid', 'payment_id': payments.id, 'qr_id': data['razorpay_qr_id'],
                    'razorpay_payment_id': data['razorpay_payment_id'], 'event_id': data['event_id'], 'last_error': False})
