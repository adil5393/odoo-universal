{
    'name': 'Inventory Multi Add',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_views.xml',
        'views/transfer_wizard_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
