import uuid
from decimal import Decimal

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_pos_qr(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_invoice'):
            raise UserError(_('Only accounting users may create POS requests.'))
        self.check_access_rights('write')
        invoices = self.line_ids.move_id
        invoices.check_access_rights('write')
        invoices.check_access_rule('write')
        if len(invoices) != 1 or not self.can_edit_wizard:
            raise UserError(_('Select exactly one customer invoice with an editable amount.'))
        invoice = invoices[0]
        if invoice.move_type != 'out_invoice' or invoice.state != 'posted' or self.payment_type != 'inbound':
            raise UserError(_('POS QR requests require a posted customer invoice.'))
        if invoice.company_id != self.company_id or invoice.currency_id.name != 'INR' or self.currency_id != invoice.currency_id:
            raise UserError(_('The invoice and payment must use INR and the same company.'))
        if invoice.partner_id.commercial_partner_id != self.partner_id.commercial_partner_id or not invoice.name or not invoice.partner_id.name:
            raise UserError(_('The invoice must have a number and matching customer.'))
        amount = Decimal(str(self.amount)) * 100
        if amount != amount.to_integral_value() or not 100 <= amount <= 100000000:
            raise UserError(_('The amount must be between INR 1 and INR 1,000,000 in whole paise.'))
        company = invoice.company_id.sudo()
        if not all([company.pos_qr_url, company.pos_qr_instance, company.pos_qr_api_key, company.pos_qr_journal_id]):
            raise UserError(_('An administrator must configure the POS URL, instance, API key and bank journal.'))
        if company.pos_qr_journal_id.company_id != company or company.pos_qr_journal_id.type != 'bank':
            raise UserError(_('The configured POS journal must be a bank journal of the invoice company.'))
        if (not company.pos_qr_instance.strip() or len(company.pos_qr_instance.strip()) > 120
                or len(invoice.name.strip()) > 120 or len(invoice.partner_id.name.strip()) > 120
                or not invoice.partner_id.name.strip()):
            raise UserError(_('POS instance, invoice number or customer name is invalid or too long.'))
        # Odoo uses repeatable-read snapshots. A no-op update forces a serialization
        # retry for concurrent reservations, so the retry sees newly reserved amounts.
        self.env.cr.execute('UPDATE account_move SET write_date = write_date WHERE id = %s', [invoice.id])
        invoice.invalidate_recordset(['amount_residual', 'state', 'payment_state'])
        active = self.env['universal.pos.request'].sudo().search([('invoice_id', '=', invoice.id), ('state', 'in', ['draft', 'uncertain', 'creating', 'ready', 'ambiguous'])])
        reserved = sum(active.mapped('amount_paise'))
        residual = int((Decimal(str(invoice.currency_id.round(invoice.amount_residual))) * 100).to_integral_value())
        if int(amount) + reserved > residual:
            raise UserError(_('The amount exceeds the unreserved invoice balance. Existing POS requests must be resolved first.'))
        record = self.env['universal.pos.request'].sudo().create({
            'reference': str(uuid.uuid4()), 'invoice_id': invoice.id, 'company_id': company.id,
            'partner_id': invoice.partner_id.id, 'invoice_number': invoice.name.strip(),
            'customer_name': invoice.partner_id.name.strip(), 'currency_id': invoice.currency_id.id,
            'amount_paise': int(amount), 'outstanding_paise': residual, 'instance': company.pos_qr_instance.strip(),
            'api_url': company.pos_qr_url, 'api_key': company.pos_qr_api_key,
            'journal_id': company.pos_qr_journal_id.id, 'requested_by_id': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window', 'name': _('POS QR Request'), 'res_model': record._name,
                'res_id': record.id, 'view_mode': 'form', 'target': 'current'}
