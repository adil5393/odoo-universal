from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseSummaryBillWizard(models.TransientModel):
    _name = 'purchase.summary.bill.wizard'
    _description = 'Create Summary (Amount Only) Vendor Bill'

    order_id = fields.Many2one('purchase.order', required=True, readonly=True)
    currency_id = fields.Many2one(related='order_id.currency_id')
    name = fields.Char(string='Description', required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True)
    tax_ids = fields.Many2many(
        'account.tax', string='Taxes',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]")
    company_id = fields.Many2one(related='order_id.company_id')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self.env['purchase.order'].browse(
            res.get('order_id') or self.env.context.get('default_order_id'))
        if order:
            res.setdefault('name', _("Purchases - %s", order.partner_id.display_name))
            res.setdefault('amount', order.amount_untaxed)
            tax_sets = {tuple(l.taxes_id.ids) for l in order.order_line if not l.display_type}
            if len(tax_sets) == 1:
                res.setdefault('tax_ids', [(6, 0, list(tax_sets.pop()))])
        return res

    def action_create_bill(self):
        self.ensure_one()
        order = self.order_id
        if self.amount <= 0:
            raise UserError(_("The amount must be greater than zero."))
        invoice_vals = order._prepare_invoice()
        invoice_vals['invoice_line_ids'] = [(0, 0, {
            'name': self.name,
            'quantity': 1,
            'price_unit': self.amount,
            'tax_ids': [(6, 0, self.tax_ids.ids)],
        })]
        move = self.env['account.move'] \
            .with_context(default_move_type='in_invoice') \
            .create(invoice_vals)
        return order.action_view_invoice(move)
