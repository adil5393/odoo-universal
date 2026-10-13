from odoo import models, fields, _
from odoo.exceptions import UserError


class MoveMultiAddWizard(models.TransientModel):
    _name = 'move.multi.add.wizard'
    _description = 'Add Multiple Products to Vendor Bill / Refund'

    state = fields.Selection([
        ('select', 'Select Products'),
        ('qty', 'Set Quantities'),
    ], default='select')

    move_id = fields.Many2one('account.move', required=True, readonly=True)
    product_ids = fields.Many2many(
        'product.product',
        'move_multi_add_product_rel',
        'wizard_id',
        'product_id',
        string='Select Products',
    )
    line_ids = fields.One2many('move.multi.add.line', 'wizard_id', string='Products')

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_load_lines(self):
        if not self.product_ids:
            raise UserError(_('Select at least one product.'))
        self.line_ids.unlink()
        self.env['move.multi.add.line'].create([
            {'wizard_id': self.id, 'product_id': p.id, 'qty': 1.0}
            for p in self.product_ids
        ])
        self.state = 'qty'
        return self._reopen()

    def action_apply(self):
        move = self.move_id
        if move.state != 'draft':
            raise UserError(_('Lines can only be added to a draft document.'))
        vals = []
        for line in self.line_ids.filtered(lambda l: l.qty > 0):
            val = {'product_id': line.product_id.id, 'quantity': line.qty}
            if line.price_unit:
                val['price_unit'] = line.price_unit
            vals.append((0, 0, val))
        if not vals:
            raise UserError(_('Enter a quantity greater than zero for at least one product.'))
        move.write({'invoice_line_ids': vals})
        return {'type': 'ir.actions.act_window_close'}


class MoveMultiAddLine(models.TransientModel):
    _name = 'move.multi.add.line'
    _description = 'Bill / Refund Multi Add Line'

    wizard_id = fields.Many2one('move.multi.add.wizard', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', readonly=True)
    qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    price_unit = fields.Float(
        string='Unit Price', digits='Product Price',
        help="Leave 0 to use the product's default price/cost.")
