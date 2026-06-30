from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InventoryMultiAddWizard(models.TransientModel):
    _name = 'inventory.multi.add.wizard'
    _description = 'Add Multiple Products to Physical Inventory'

    state = fields.Selection([
        ('select', 'Select Products'),
        ('qty', 'Set Quantities'),
    ], default='select')

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain=[('usage', '=', 'internal')],
        required=True,
    )
    product_ids = fields.Many2many(
        'product.product',
        'inventory_multi_add_product_rel',
        'wizard_id',
        'product_id',
        string='Select Products',
        domain=[('type', 'in', ['product', 'consu'])],
    )
    line_ids = fields.One2many('inventory.multi.add.line', 'wizard_id', string='Products')

    def action_load_lines(self):
        """Step 1 → Step 2: create real DB line records then switch to qty view."""
        if not self.location_id:
            raise UserError(_('Select a location first.'))
        if not self.product_ids:
            raise UserError(_('Select at least one product.'))

        # Wipe old lines and create fresh DB records for each selected product
        self.line_ids.unlink()
        lines = []
        for product in self.product_ids:
            lines.append({
                'wizard_id': self.id,
                'product_id': product.id,
                'qty': 0.0,
            })
        self.env['inventory.multi.add.line'].create(lines)
        self.state = 'qty'

        # Re-open the same wizard record (lines now exist in DB)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.multi.add.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_apply(self):
        """Step 2: write inventory_quantity on each quant."""
        if not self.line_ids:
            raise UserError(_('No lines found. Go back and select products first.'))

        Quant = self.env['stock.quant'].sudo()
        today = fields.Date.today()

        for line in self.line_ids:
            if not line.product_id:
                continue

            quant = Quant.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', self.location_id.id),
                ('lot_id', '=', False),
                ('package_id', '=', False),
                ('owner_id', '=', False),
            ], limit=1)

            if quant:
                quant.inventory_quantity = line.qty
                quant.inventory_date = today
            else:
                new_quant = Quant.with_context(inventory_mode=True).create({
                    'product_id': line.product_id.id,
                    'location_id': self.location_id.id,
                    'inventory_quantity': line.qty,
                })

        return self.env['stock.quant'].action_view_inventory()


class InventoryMultiAddLine(models.TransientModel):
    _name = 'inventory.multi.add.line'
    _description = 'Inventory Multi Add Line'

    wizard_id = fields.Many2one(
        'inventory.multi.add.wizard', ondelete='cascade', required=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Product', readonly=True,
    )
    uom_id = fields.Many2one(
        'uom.uom', string='UoM', related='product_id.uom_id', readonly=True,
    )
    qty = fields.Float(
        string='Counted Quantity', digits='Product Unit of Measure', default=0.0,
    )
