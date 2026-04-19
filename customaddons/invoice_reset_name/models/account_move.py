from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _irn_get_fy_suffix(self, invoice_date):
        """2-digit FY starting year. India FY April–March.
        e.g. April 2026 → FY2026-27 → '26'
        """
        year = invoice_date.year
        month = invoice_date.month
        fy_start_year = year if month >= 4 else year - 1
        return str(fy_start_year)[-2:]

    def _irn_get_type_prefix(self):
        """Returns sequence prefix based on move type and tax:
        - Customer invoice with tax    → TX
        - Customer invoice without tax → BS
        - Credit note with tax         → RTX
        - Credit note without tax      → RBS
        """
        base = 'TX' if self.amount_tax != 0 else 'BS'
        return f'R{base}' if self.move_type == 'out_refund' else base

    def _irn_get_or_create_sequence(self, prefix_code, fy):
        """Get or create an ir.sequence for the given type+FY combination.
        Always syncs number_next from the DB to prevent duplicates.
        """
        seq_code = f'invoice.{prefix_code.lower()}.{fy}'
        seq_prefix = f'{prefix_code}{fy}/'

        # Find max existing sequence number in DB for this prefix
        self.env.cr.execute(
            """SELECT COALESCE(MAX(sequence_number), 0)
                 FROM account_move
                WHERE sequence_prefix = %s
                  AND state = 'posted'""",
            (seq_prefix,),
        )
        db_max = self.env.cr.fetchone()[0]
        next_num = db_max + 1

        sequence = self.env['ir.sequence'].sudo().search(
            [('code', '=', seq_code), ('company_id', '=', self.company_id.id)],
            limit=1,
        )
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': f'{prefix_code}{fy} Sequence',
                'code': seq_code,
                'prefix': seq_prefix,
                'padding': 5,
                'company_id': self.company_id.id,
                'number_next': next_num,
                'number_increment': 1,
            })
        elif sequence.number_next <= db_max:
            # Sequence is behind — catch up to avoid duplicates
            sequence.sudo().write({'number_next': next_num})
        return sequence

    def _irn_get_journal(self, prefix_code):
        """Find TX or BS journal by name. Strips leading R for credit notes."""
        journal_name = prefix_code.lstrip('R')  # RTX → TX, RBS → BS
        return self.env['account.journal'].sudo().search(
            [('name', '=', journal_name), ('company_id', '=', self.company_id.id)],
            limit=1,
        )

    def _irn_applicable(self):
        return self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund'))

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------

    def _must_check_constrains_date_sequence(self):
        if self.name and any(self.name.startswith(p) for p in ('TX', 'BS', 'RTX', 'RBS')):
            return False
        return super()._must_check_constrains_date_sequence()

    def _set_next_sequence(self):
        """Use our custom sequences for customer invoices and credit notes."""
        if self.move_type not in ('out_invoice', 'out_refund'):
            return super()._set_next_sequence()

        invoice_date = self.invoice_date or fields.Date.today()
        prefix_code = self._irn_get_type_prefix()
        fy = self._irn_get_fy_suffix(invoice_date)
        sequence = self._irn_get_or_create_sequence(prefix_code, fy)
        self.name = sequence.next_by_code(sequence.code)

    def action_post(self):
        # Switch journal via SQL BEFORE posting to avoid archived journal errors.
        # SQL bypasses ORM write() so Odoo's sequence logic never fires on journal change.
        for move in self._irn_applicable().filtered(lambda m: m.state == 'draft'):
            prefix_code = move._irn_get_type_prefix()
            journal = move._irn_get_journal(prefix_code)
            if journal and journal.id != move.journal_id.id:
                self.env.cr.execute(
                    "UPDATE account_move SET journal_id = %s WHERE id = %s",
                    (journal.id, move.id),
                )
        self.env['account.move'].invalidate_model(['journal_id'])

        result = super().action_post()

        # Sync sequence_prefix and sequence_number stored fields to match our name
        for move in self._irn_applicable().filtered(lambda m: m.state == 'posted'):
            if move.name and '/' in move.name:
                seq_prefix = move.name.split('/')[0] + '/'
                seq_number = int(move.name.split('/')[1])
                self.env.cr.execute(
                    "UPDATE account_move SET sequence_prefix = %s, sequence_number = %s WHERE id = %s",
                    (seq_prefix, seq_number, move.id),
                )
        self.env['account.move'].invalidate_model(['sequence_prefix', 'sequence_number'])
        return result
