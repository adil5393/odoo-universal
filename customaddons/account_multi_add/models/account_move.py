from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_multi_add(self):
        wizard = self.env['move.multi.add.wizard'].create({'move_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'move.multi.add.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
