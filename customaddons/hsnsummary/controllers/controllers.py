# -*- coding: utf-8 -*-
# from odoo import http


# class Hsnsummary(http.Controller):
#     @http.route('/hsnsummary/hsnsummary', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hsnsummary/hsnsummary/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hsnsummary.listing', {
#             'root': '/hsnsummary/hsnsummary',
#             'objects': http.request.env['hsnsummary.hsnsummary'].search([]),
#         })

#     @http.route('/hsnsummary/hsnsummary/objects/<model("hsnsummary.hsnsummary"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hsnsummary.object', {
#             'object': obj
#         })

