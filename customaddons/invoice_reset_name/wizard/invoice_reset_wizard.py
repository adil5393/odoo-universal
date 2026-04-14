from odoo import models, fields, api


class InvoiceResetNameWizard(models.TransientModel):
    _name = 'invoice.reset.name.wizard'
    _description = 'Bulk Reset Customer Invoice Names'

    date_from = fields.Date('From Date')
    date_to = fields.Date('To Date')
    preview_html = fields.Html('Preview', readonly=True, sanitize=False)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_fy_suffix(self, invoice_date):
        """Return 2-digit financial year ending suffix.
        India FY: April–March. e.g. June 2025 → FY2025-26 → '26'
        """
        year = invoice_date.year
        month = invoice_date.month
        fy_start_year = year if month >= 4 else year - 1
        return str(fy_start_year)[-2:]

    def _get_invoice_type(self, move):
        """Return 'TX' if invoice has any tax, else 'BS'."""
        return 'TX' if move.amount_tax != 0 else 'BS'

    def _build_invoice_domain(self):
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        return domain

    def _compute_new_names(self):
        """Return list of (move, new_name) sorted oldest first."""
        moves = self.env['account.move'].search(
            self._build_invoice_domain(),
            order='invoice_date asc, id asc',
        )
        counters = {}
        result = []
        for move in moves:
            inv_type = self._get_invoice_type(move)
            fy = self._get_fy_suffix(move.invoice_date)
            key = (inv_type, fy)
            counters[key] = counters.get(key, 0) + 1
            new_name = f'{inv_type}{fy}/{counters[key]:05d}'
            result.append((move, new_name))
        return result

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_preview(self):
        pairs = self._compute_new_names()
        if not pairs:
            self.preview_html = '<p>No posted invoices found for the selected period.</p>'
            return {'type': 'ir.actions.act_window', 'res_model': self._name,
                    'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

        rows = ''.join(
            f'<tr>'
            f'<td style="padding:4px 12px 4px 4px">{move.name}</td>'
            f'<td style="padding:4px 12px 4px 4px">{move.invoice_date}</td>'
            f'<td style="padding:4px 4px 4px 4px;color:#007b5e;font-weight:bold">{new_name}</td>'
            f'</tr>'
            for move, new_name in pairs
        )
        self.preview_html = (
            f'<table style="border-collapse:collapse;font-size:13px">'
            f'<thead><tr>'
            f'<th style="padding:4px 12px 4px 4px;text-align:left">Current Name</th>'
            f'<th style="padding:4px 12px 4px 4px;text-align:left">Invoice Date</th>'
            f'<th style="padding:4px 4px 4px 4px;text-align:left">New Name</th>'
            f'</tr></thead>'
            f'<tbody>{rows}</tbody>'
            f'</table>'
        )
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def _sync_sequences(self, pairs):
        """After bulk rename, set each ir.sequence to continue from the last used number."""
        # Find highest counter per (type, fy) key
        last_counters = {}
        for _move, new_name in pairs:
            # new_name format: TX26/00045
            prefix_code, num_str = new_name.split('/')
            inv_type = prefix_code[:2]       # 'TX' or 'BS'
            fy = prefix_code[2:]             # '26'
            key = (inv_type, fy)
            last_counters[key] = max(last_counters.get(key, 0), int(num_str))

        company_id = self.env.company.id
        for (inv_type, fy), last_num in last_counters.items():
            seq_code = f'invoice.{inv_type.lower()}.{fy}'
            sequence = self.env['ir.sequence'].sudo().search(
                [('code', '=', seq_code), ('company_id', '=', company_id)],
                limit=1,
            )
            if sequence:
                sequence.sudo().write({'number_next': last_num + 1})
            else:
                self.env['ir.sequence'].sudo().create({
                    'name': f'{inv_type}{fy} Invoice Sequence',
                    'code': seq_code,
                    'prefix': f'{inv_type}{fy}/',
                    'padding': 5,
                    'company_id': company_id,
                    'number_next': last_num + 1,
                    'number_increment': 1,
                })

    def action_apply(self):
        pairs = self._compute_new_names()
        if not pairs:
            return {'type': 'ir.actions.act_window_close'}

        for move, new_name in pairs:
            seq_prefix, seq_num_str = new_name.split('/')
            seq_prefix += '/'
            seq_number = int(seq_num_str)
            self.env.cr.execute(
                "UPDATE account_move SET name = %s, sequence_prefix = %s, sequence_number = %s WHERE id = %s",
                (new_name, seq_prefix, seq_number, move.id),
            )

        # Invalidate cache so views reflect the new names immediately
        self.env['account.move'].invalidate_model(['name', 'sequence_prefix', 'sequence_number'])

        # Sync sequences so future invoices continue from the right number
        self._sync_sequences(pairs)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invoice Names Reset',
                'message': f'{len(pairs)} invoice(s) have been renamed successfully.',
                'type': 'success',
                'sticky': False,
            },
        }
