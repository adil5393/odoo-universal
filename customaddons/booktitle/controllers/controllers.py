# -*- coding: utf-8 -*-
# from odoo import http


# class Booktitle(http.Controller):
#     @http.route('/booktitle/booktitle', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/booktitle/booktitle/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('booktitle.listing', {
#             'root': '/booktitle/booktitle',
#             'objects': http.request.env['booktitle.booktitle'].search([]),
#         })

#     @http.route('/booktitle/booktitle/objects/<model("booktitle.booktitle"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('booktitle.object', {
#             'object': obj
#         })

