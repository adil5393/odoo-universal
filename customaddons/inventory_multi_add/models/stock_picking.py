from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_open_multi_add(self):
        wizard = self.env['transfer.multi.add.wizard'].create({
            'picking_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transfer.multi.add.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
