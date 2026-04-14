from odoo import models, fields,api

class SaleOrderInherit(models.Model):
    _inherit = "sale.order.line"
    booktitle = fields.Many2one(
        'product.tag',
        string="Name",
        store=True,
        ondelete='set null'
    )
    available_tags = fields.Many2many(
        'product.tag', 
        string="Available Tags", 
        compute="_compute_available_tags"
    )
    @api.depends('product_id')
    def _compute_available_tags(self):
        for line in self:
            if line.product_id:
                available_tags = line.product_id.additional_product_tag_ids
                line.available_tags = available_tags  # Assign all available tags

                # Preserve selection if still in available tags
                if line.booktitle and line.booktitle in available_tags:
                    continue
                elif len(available_tags) == 1:
                    line.booktitle = available_tags[0]
                else:
                    line.booktitle = False  # Keep it empty for selection
            else:
                line.available_tags = [(5, 0, 0)]
                line.booktitle = False  # Reset selection if no product

class StockMoveInherit(models.Model):
    _inherit = 'stock.move'
    booktitle = fields.Char("Name", compute="_compute_a", store=True)
    
    @api.depends('product_id', 'origin')
    def _compute_a(self):
        for record in self:
            book_title = None
            if record.origin:
                sale_order = self.env['sale.order'].search([('name', '=', record.origin)], limit=1)
                if sale_order:
                    sale_line = self.env['sale.order.line'].search([
                        ('order_id', '=', sale_order.id),
                        ('product_id', '=', record.product_id.id)
                    ], limit=1)
                    if sale_line and sale_line.booktitle:
                        book_title = sale_line.booktitle.name
            record.booktitle = book_title or ""
            
class AccountMoveLine(models.Model):
    _inherit='account.move.line'
    booktitle = fields.Char("Name", compute="_compute_booktitle", store=True)
    
    @api.depends('sale_line_ids')
    def _compute_booktitle(self):
        for line in self:
            book_title = ""
            if line.sale_line_ids:
                for sale_line in line.sale_line_ids:
                    if sale_line.booktitle:
                        book_title = sale_line.booktitle.name  # Fetch the booktitle from sale.order.line
                        break  # Use the first found booktitle (if there are multiple sale lines)
            line.booktitle = book_title
