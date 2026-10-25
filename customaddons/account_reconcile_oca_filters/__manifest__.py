{
    "name": "Reconcile Screen Filters",
    "summary": "Hide cash journal items when matching bank lines, group by journal, "
    "keep the chosen filters on the next bank line, and keep the list position when picking items",
    "version": "17.0.1.1.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": ["account_reconcile_oca"],
    "data": ["views/account_move_line_views.xml"],
    "assets": {
        "web.assets_backend": [
            "account_reconcile_oca_filters/static/src/js/*.esm.js",
        ],
    },
    "installable": True,
}
