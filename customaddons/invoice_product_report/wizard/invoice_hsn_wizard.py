from odoo import models, fields
from io import BytesIO
import base64
import xlsxwriter

class InvoiceProductReportWizard(models.TransientModel):
    _name = 'invoice.product.hsn.wizard'
    _description = 'Wizard for Invoice Product Report'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    def generate_report(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('HSN Summary Report')

        headers = ['Invoice No', 'Date', 'Customer', 'HSN/SAC', 'Quantity', 'UoM', 'Rate', 'Untaxed', 'IGST', 'CGST', 'SGST', 'Cess']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ])
        
        row = 1
        for inv in invoices:
            hsn_data = inv._l10n_in_get_hsn_summary_table()
            for item in hsn_data.get('items', []):
                worksheet.write(row, 0, inv.name or '')
                worksheet.write(row, 1, str(inv.invoice_date or ''))
                worksheet.write(row, 2, inv.partner_id.name or '')
                worksheet.write(row, 3, item.get('l10n_in_hsn_code', ''))
                worksheet.write(row, 4, item.get('quantity', 0.0))
                worksheet.write(row, 5, item.get('uom', '').name if item.get('uom') else '')
                worksheet.write(row, 6, item.get('rate', 0.0))
                worksheet.write(row, 7, item.get('amount_untaxed', 0.0))
                worksheet.write(row, 8, item.get('tax_amount_igst', 0.0))
                worksheet.write(row, 9, item.get('tax_amount_cgst', 0.0))
                worksheet.write(row, 10, item.get('tax_amount_sgst', 0.0))
                worksheet.write(row, 11, item.get('tax_amount_cess', 0.0))
                row += 1

        workbook.close()
        output.seek(0)
        report_data = output.read()
        output.close()

        file_name = 'hsn_summary_report.xlsx'
        file_base64 = base64.b64encode(report_data)

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_base64,
            'res_model': 'invoice.product.hsn.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        download_url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
