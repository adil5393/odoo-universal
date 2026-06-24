# -*- coding: utf-8 -*-
{
    'name': "Vendor Ledger",
    'summary': "Print a chronological vendor ledger with purchases, payments and refunds",
    'author': "My Company",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'report/vendor_ledger_report.xml',
        'views/vendor_ledger_wizard_views.xml',
        'views/menu.xml',
    ],
}
