from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    pos_qr_url = fields.Char(string='POS API base URL', groups='base.group_system')
    pos_qr_instance = fields.Char(string='POS instance', groups='base.group_system')
    pos_qr_api_key = fields.Char(string='POS API key', groups='base.group_system', copy=False)
    pos_qr_journal_id = fields.Many2one('account.journal', string='POS bank journal',
        domain="[('type', '=', 'bank'), ('company_id', '=', id)]", groups='base.group_system', check_company=True)
