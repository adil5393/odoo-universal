from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TransferMultiAddWizard(models.TransientModel):
    _name = 'transfer.multi.add.wizard'
    _description = 'Add Multiple Products to Internal Transfer'

    state = fields.Selection([
        ('select', 'Select Products'),
        ('qty', 'Set Quantities'),
    ], default='select')

    picking_id = fields.Many2one('stock.picking', required=True, readonly=True)
    product_ids = fields.Many2many(
        'product.product',
        'transfer_multi_add_product_rel',
        'wizard_id',
        'product_id',
        string='Select Products',
        domain=[('type', 'in', ['product', 'consu'])],
    )
    line_ids = fields.One2many('transfer.multi.add.line', 'wizard_id', string='Products')

    def action_load_lines(self):
        if not self.product_ids:
            raise UserError(_('Select at least one product.'))

        self.line_ids.unlink()
        self.env['transfer.multi.add.line'].create([
            {'wizard_id': self.id, 'product_id': p.id, 'qty': 0.0}
            for p in self.product_ids
        ])
        self.state = 'qty'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transfer.multi.add.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_apply(self):
        if not self.line_ids:
            raise UserError(_('No lines found. Go back and select products first.'))

        picking = self.picking_id
        new_moves = self.env['stock.move']

        for line in self.line_ids:
            if not line.product_id or line.qty <= 0:
                continue
            move = self.env['stock.move'].create({
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'company_id': picking.company_id.id,
            })
            new_moves |= move

        if new_moves and picking.state not in ('draft', 'cancel', 'done'):
            new_moves._action_confirm()
            new_moves._action_assign()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
            'target': 'current',
        }


class TransferMultiAddLine(models.TransientModel):
    _name = 'transfer.multi.add.line'
    _description = 'Transfer Multi Add Line'

    wizard_id = fields.Many2one(
        'transfer.multi.add.wizard', ondelete='cascade', required=True,
    )
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    uom_id = fields.Many2one(
        'uom.uom', string='UoM', related='product_id.uom_id', readonly=True,
    )
    qty = fields.Float(
        string='Quantity', digits='Product Unit of Measure', default=0.0,
    )
