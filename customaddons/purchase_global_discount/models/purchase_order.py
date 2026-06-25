from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    global_discount = fields.Float(
        string='Global Discount (%)',
        digits='Discount',
    )

    def action_apply_global_discount(self):
        for order in self:
            if order.state in ('done', 'cancel'):
                raise UserError("Cannot modify a locked or cancelled purchase order.")
            for line in order.order_line:
                if line.display_type:
                    continue
                line.discount = order.global_discount
