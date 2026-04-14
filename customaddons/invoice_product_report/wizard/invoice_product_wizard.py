from odoo import models, fields
from io import BytesIO
import base64
import xlsxwriter

class InvoiceProductReportWizard(models.TransientModel):
    _name = 'invoice.product.report.wizard'
    _description = 'Wizard for Invoice Product Report'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    def generate_report(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Invoice Product Report')

        headers = ['Invoice No', 'Date', 'Customer', 'Product', 'HSN/SAC', 'Quantity', 'Unit Price', 'Subtotal', 'Tax Amount', 'Total']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        domain = [
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
        ]

        lines = self.env['account.move.line'].search(domain)
        row = 1

        for line in lines:
            if not line.product_id and line.product_id != False:
                # If line doesn't have a product_id, we need to check if it's a valid service or discount
                if line.name not in ['Discount', 'Tax']:
                    continue  # Skip lines that don't have a product and are not discounts or taxe
            inv = line.move_id
            product = line.product_id
            taxes = sum(t.amount for t in line.tax_ids)
            total = line.price_subtotal + (line.price_subtotal*(taxes/100))

            worksheet.write(row, 0, inv.name or '')
            worksheet.write(row, 1, str(inv.invoice_date or ''))
            worksheet.write(row, 2, inv.partner_id.name or '')
            worksheet.write(row, 3, product.name or '')
            worksheet.write(row, 4, product.l10n_in_hsn_code or '')
            worksheet.write(row, 5, line.quantity)
            worksheet.write(row, 6, line.price_unit)
            worksheet.write(row, 7, line.price_subtotal)
            worksheet.write(row, 8, taxes)
            worksheet.write(row, 9, total)
            row += 1

        workbook.close()
        output.seek(0)
        report_data = output.read()
        output.close()

        file_name = 'invoice_product_report.xlsx'
        file_base64 = base64.b64encode(report_data)

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_base64,
            'res_model': 'invoice.product.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        download_url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }



