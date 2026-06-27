# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VendorLedgerWizard(models.TransientModel):
    _name = 'vendor.ledger.wizard'
    _description = 'Vendor Ledger Report'

    vendor_id = fields.Many2one(
        'res.partner', string='Vendor', required=True,
        domain=[('supplier_rank', '>', 0)])
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(
        string='To Date', required=True,
        default=fields.Date.context_today)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_('From Date must be earlier than To Date.'))

    def _get_ledger_data(self):
        """Return opening balance, chronological lines, and closing balance."""
        self.ensure_one()

        payable_type = 'liability_payable'

        # Opening balance: all posted payable lines before date_from
        opening_lines = self.env['account.move.line'].search([
            ('partner_id', '=', self.vendor_id.id),
            ('account_id.account_type', '=', payable_type),
            ('move_id.state', '=', 'posted'),
            ('date', '<', self.date_from),
        ])
        opening_balance = sum(l.credit - l.debit for l in opening_lines)

        # Period lines
        period_lines = self.env['account.move.line'].search([
            ('partner_id', '=', self.vendor_id.id),
            ('account_id.account_type', '=', payable_type),
            ('move_id.state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ], order='date asc, move_id asc, id asc')

        lines = []
        balance = opening_balance
        total_purchases = 0.0
        total_payments = 0.0
        total_refunds = 0.0

        for ml in period_lines:
            move = ml.move_id
            credit = ml.credit   # bills: vendor charges us → balance goes up
            debit = ml.debit     # payments / refunds → balance goes down
            balance += credit - debit

            if move.payment_id:
                entry_type = _('Payment')
                total_payments += debit
            elif move.move_type == 'in_invoice':
                entry_type = _('Purchase')
                total_purchases += credit
            elif move.move_type == 'in_refund':
                entry_type = _('Refund')
                total_refunds += debit
            else:
                entry_type = _('Journal Entry')
                if credit:
                    total_purchases += credit
                else:
                    total_payments += debit

            lines.append({
                'date': ml.date,
                'reference': move.name or '',
                'memo': move.ref or '',
                'type': entry_type,
                'purchase': credit if entry_type == _('Purchase') else 0.0,
                'payment': debit if entry_type == _('Payment') else 0.0,
                'refund': debit if entry_type == _('Refund') else 0.0,
                'balance': balance,
            })

        return {
            'vendor': self.vendor_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.env.company.currency_id,
            'opening_balance': opening_balance,
            'lines': lines,
            'total_purchases': total_purchases,
            'total_payments': total_payments,
            'total_refunds': total_refunds,
            'closing_balance': balance,
        }

    def action_print_ledger(self):
        self.ensure_one()
        return self.env.ref(
            'vendor_ledger.action_report_vendor_ledger'
        ).report_action(self)
