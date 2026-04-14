{
    'name': 'Invoice Reset Name',
    'version': '17.0.1.0.0',
    'summary': 'Bulk reset posted customer invoice names to TX/BS format',
    'category': 'Accounting',
    'author': 'Adil',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/invoice_reset_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
