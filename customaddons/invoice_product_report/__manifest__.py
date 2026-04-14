{
    'name': 'Invoice Product Report',
    'version': '1.0',
    'summary': 'Generate product sales report based on posted invoices',
    'category': 'Sales',
    'author': 'Adil & ChatGPT',
    'depends': ['base', 'sale', 'account'],
    'data': [
    'security/ir.model.access.csv',
    'views/invoice_product_report_action.xml',  # ← This defines the action
    'views/invoice_hsn_report_action.xml',
    'views/invoice_product_report_menu.xml',    # ← This uses the action ID
    
],
    'installable': True,
}
