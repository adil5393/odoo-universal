# -*- coding: utf-8 -*-

from odoo import models, fields, api


class no_print_variant_grid(models.Model):
    _inherit = 'sale.order'
    report_grids = fields.Boolean(default = False,store=True)
    
    

