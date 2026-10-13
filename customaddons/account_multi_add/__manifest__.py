{
    'name': 'Bill / Refund Multi Add',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add multiple products at once to vendor bills and vendor refunds',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
