# -*- coding: utf-8 -*-
{
    'name': "Warehouse Transfer",
    'summary': "Transfer all stock items from one warehouse to another",
    'description': """
        Provides a wizard under Inventory > Operations to move all available
        stock from a source warehouse to a destination warehouse in a single
        internal transfer picking.
    """,
    'author': "My Company",
    'category': 'Inventory',
    'version': '17.0.1.0.0',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/warehouse_transfer_wizard_views.xml',
        'views/menu.xml',
    ],
}
