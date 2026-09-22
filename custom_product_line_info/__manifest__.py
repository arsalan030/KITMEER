{
    'name': 'Custom Product Line Info',
    'version': '19.0.1.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Add Internal Reference and Description to all document lines',
    'depends': ['sale', 'purchase', 'stock', 'account'],
    'data': [
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_move_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}