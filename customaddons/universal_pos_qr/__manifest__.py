{
    'name': 'Universal POS QR Payments',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': ['security/security.xml', 'security/ir.model.access.csv',
             'views/res_company_views.xml', 'views/pos_request_views.xml',
             'views/account_payment_register_views.xml'],
    'installable': True,
}
