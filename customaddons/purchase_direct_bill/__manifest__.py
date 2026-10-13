{
    'name': "Purchase Direct Bill",
    'summary': "Create a vendor bill directly from a purchase order's lines, bypassing delivered/received quantity control",
    'author': "My Company",
    'category': 'Purchase',
    'version': '17.0.1.0.0',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/summary_bill_wizard_views.xml',
        'views/purchase_order_views.xml',
    ],
}
