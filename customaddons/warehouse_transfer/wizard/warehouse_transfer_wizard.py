# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WarehouseTransferWizard(models.TransientModel):
    _name = 'warehouse.transfer.wizard'
    _description = 'Transfer All Stock Between Warehouses'

    source_warehouse_id = fields.Many2one(
        'stock.warehouse', string='Source Warehouse', required=True)
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse', string='Destination Warehouse', required=True)
    scheduled_date = fields.Datetime(
        string='Scheduled Date', default=fields.Datetime.now, required=True)

    @api.constrains('source_warehouse_id', 'dest_warehouse_id')
    def _check_warehouses(self):
        for rec in self:
            if rec.source_warehouse_id == rec.dest_warehouse_id:
                raise UserError(_('Source and destination warehouses must be different.'))

    def action_transfer(self):
        self.ensure_one()

        src_wh = self.source_warehouse_id
        dest_wh = self.dest_warehouse_id

        # Find all quants with positive quantity in the source warehouse
        quants = self.env['stock.quant'].search([
            ('location_id', 'child_of', src_wh.view_location_id.id),
            ('location_id.usage', '=', 'internal'),
            ('quantity', '>', 0),
        ])

        if not quants:
            raise UserError(
                _('No stock found in warehouse "%s".') % src_wh.name
            )

        # Build one move per quant so each source location and lot are preserved
        move_vals_list = []
        for quant in quants:
            move_vals_list.append((0, 0, {
                'name': quant.product_id.display_name,
                'product_id': quant.product_id.id,
                'product_uom': quant.product_uom_id.id,
                'product_uom_qty': quant.quantity,
                'location_id': quant.location_id.id,
                'location_dest_id': dest_wh.lot_stock_id.id,
            }))

        picking = self.env['stock.picking'].create({
            'picking_type_id': src_wh.int_type_id.id,
            'location_id': src_wh.lot_stock_id.id,
            'location_dest_id': dest_wh.lot_stock_id.id,
            'scheduled_date': self.scheduled_date,
            'origin': _('Warehouse Transfer: %s → %s') % (
                src_wh.name, dest_wh.name),
            'move_ids': move_vals_list,
        })

        # Confirm and reserve stock
        picking.action_confirm()
        picking.action_assign()

        # Mark all reserved quantities as done (Odoo 17 uses `quantity` on move lines)
        for move_line in picking.move_line_ids:
            move_line.quantity = move_line.quantity_product_uom

        # Validate immediately — skip_backorder avoids the backorder wizard
        picking.with_context(skip_backorder=True).button_validate()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Warehouse Transfer'),
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current',
        }
