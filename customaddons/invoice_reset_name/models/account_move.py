from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # Helpers (same logic as wizard)
    # -------------------------------------------------------------------------

    def _irn_get_fy_suffix(self, invoice_date):
        """2-digit FY ending year. India FY April–March.
        e.g. June 2025 → FY2025-26 → '26'
        """
        year = invoice_date.year
        month = invoice_date.month
        fy_start_year = year if month >= 4 else year - 1
        return str(fy_start_year)[-2:]

    def _irn_get_type_prefix(self):
        """'TX' if invoice has tax, else 'BS'."""
        return 'TX' if self.amount_tax != 0 else 'BS'

    def _irn_get_or_create_sequence(self, prefix_code, fy):
        """Get or create an ir.sequence for the given type+FY combination."""
        seq_code = f'invoice.{prefix_code.lower()}.{fy}'
        sequence = self.env['ir.sequence'].sudo().search(
            [('code', '=', seq_code), ('company_id', '=', self.company_id.id)],
            limit=1,
        )
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': f'{prefix_code}{fy} Invoice Sequence',
                'code': seq_code,
                'prefix': f'{prefix_code}{fy}/',
                'padding': 5,
                'company_id': self.company_id.id,
                'number_next': 1,
                'number_increment': 1,
            })
        return sequence

    # -------------------------------------------------------------------------
    # Override
    # -------------------------------------------------------------------------

    def _must_check_constrains_date_sequence(self):
        """Skip Odoo's calendar-year date validation for TX/BS sequences.
        Our sequences use financial year (April–March), not calendar year,
        so the year suffix will never match Odoo's expectation.
        """
        if self.name and (self.name.startswith('TX') or self.name.startswith('BS')):
            return False
        return super()._must_check_constrains_date_sequence()

    def action_post(self):
        result = super().action_post()
        for move in self.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
        ):
            invoice_date = move.invoice_date or fields.Date.today()
            prefix_code = move._irn_get_type_prefix()
            fy = move._irn_get_fy_suffix(invoice_date)
            sequence = move._irn_get_or_create_sequence(prefix_code, fy)
            new_name = sequence.next_by_code(sequence.code)
            seq_prefix = f'{prefix_code}{fy}/'
            seq_number = int(new_name.split('/')[1])
            self.env.cr.execute(
                "UPDATE account_move SET name = %s, sequence_prefix = %s, sequence_number = %s WHERE id = %s",
                (new_name, seq_prefix, seq_number, move.id),
            )
        self.env['account.move'].invalidate_model(['name', 'sequence_prefix', 'sequence_number'])
        return result
