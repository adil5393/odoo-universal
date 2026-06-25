from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_in_get_hsn_summary_table(self):
        result = super()._l10n_in_get_hsn_summary_table()

        # Distribute any invoice-level discount lines (negative-amount lines with no HSN code)
        # proportionally across HSN groups so amount_untaxed matches the UI total.
        discount_total = sum(
            l.price_subtotal
            for l in self.invoice_line_ids
            if not l.product_id.l10n_in_hsn_code and l.price_subtotal < 0
        )

        if discount_total:
            untaxed_total = sum(item['amount_untaxed'] for item in result['items'])
            if untaxed_total:
                for item in result['items']:
                    item['amount_untaxed'] += (item['amount_untaxed'] / untaxed_total) * discount_total

        return result
