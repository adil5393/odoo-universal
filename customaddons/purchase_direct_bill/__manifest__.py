{
    'name': "Purchase Direct Bill",
    'summary': "Create a vendor bill directly from a purchase order's lines, bypassing delivered/received quantity control",
    'author': "My Company",
    'category': 'Purchase',
    'version': '17.0.1.0.0',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
}
