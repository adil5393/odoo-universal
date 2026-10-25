{
    "name": "Reconcile Screen Filters",
    "summary": "Hide cash journal items when matching bank lines, group by journal, "
    "and keep the chosen filters when moving to the next bank line",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": ["account_reconcile_oca"],
    "data": ["views/account_move_line_views.xml"],
    "assets": {
        "web.assets_backend": [
            "account_reconcile_oca_filters/static/src/js/remember_filters.esm.js",
        ],
    },
    "installable": True,
}
