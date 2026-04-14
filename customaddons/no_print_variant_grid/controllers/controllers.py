# -*- coding: utf-8 -*-
# from odoo import http


# class NoPrintVariantGrid(http.Controller):
#     @http.route('/no_print_variant_grid/no_print_variant_grid', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/no_print_variant_grid/no_print_variant_grid/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('no_print_variant_grid.listing', {
#             'root': '/no_print_variant_grid/no_print_variant_grid',
#             'objects': http.request.env['no_print_variant_grid.no_print_variant_grid'].search([]),
#         })

#     @http.route('/no_print_variant_grid/no_print_variant_grid/objects/<model("no_print_variant_grid.no_print_variant_grid"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('no_print_variant_grid.object', {
#             'object': obj
#         })

