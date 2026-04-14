# -*- coding: utf-8 -*-
# from odoo import http


# class InvoiceProductReport(http.Controller):
#     @http.route('/invoice_product_report/invoice_product_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/invoice_product_report/invoice_product_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('invoice_product_report.listing', {
#             'root': '/invoice_product_report/invoice_product_report',
#             'objects': http.request.env['invoice_product_report.invoice_product_report'].search([]),
#         })

#     @http.route('/invoice_product_report/invoice_product_report/objects/<model("invoice_product_report.invoice_product_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('invoice_product_report.object', {
#             'object': obj
#         })

