{
    'name': "Invoice / Bill without Amount",
    'summary': "Adds an 'Invoice without Amount' print option (description & quantity only, no prices/totals) for invoices, bills and refunds",
    'author': "My Company",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account'],
    'data': [
        'report/report_invoice_no_amount.xml',
        'views/account_report_actions.xml',
    ],
}
