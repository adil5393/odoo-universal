from odoo import _, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_create_direct_bill(self):
        """Create a vendor bill by copying the purchase order lines as-is.

        Unlike action_create_invoice(), this ignores the invoice policy
        (delivered/ordered quantities) and does not link the bill lines back
        to the purchase order lines, so it works even when nothing has been
        received yet.
        """
        moves = self.env['account.move']
        for order in self:
            if order.state not in ('purchase', 'done'):
                raise UserError(_("You can only create a bill for a confirmed purchase order."))

            product_lines = order.order_line.filtered(lambda l: not l.display_type)
            if not product_lines:
                raise UserError(_("There are no order lines to bill."))

            invoice_vals = order._prepare_invoice()
            pending_section = None
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if line.display_type == 'line_note':
                    invoice_vals['invoice_line_ids'].append((0, 0, {
                        'display_type': line.display_type,
                        'name': line.name,
                    }))
                    continue
                if pending_section:
                    invoice_vals['invoice_line_ids'].append((0, 0, {
                        'display_type': pending_section.display_type,
                        'name': pending_section.name,
                    }))
                    pending_section = None
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'name': line.name,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom.id,
                    'quantity': line.product_qty,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'tax_ids': [(6, 0, line.taxes_id.ids)],
                    'analytic_distribution': line.analytic_distribution,
                }))

            moves |= self.env['account.move'] \
                .with_context(default_move_type='in_invoice') \
                .create(invoice_vals)

        return self.action_view_invoice(moves)
