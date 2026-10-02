# -*- coding: utf-8 -*-
{
    'name': 'Universal Dark Theme',
    'version': '17.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': 'Enterprise Graphite Dark Theme for Odoo 17 Backend',
    'description': """
Universal Dark Theme for Odoo 17
================================
A professional, modern enterprise dark theme crafted specifically for Odoo 17:
- Restrained dark charcoal / graphite palette avoiding harsh pure black
- High-contrast, fatigue-free readable typography
- Beautiful subtle elevation and refined borders
- Full backend support: Top Navbar, Control Panel, Breadcrumbs, Search, List Views, Form Views, Kanban Cards, Modals, Dropdowns, Datepickers, Chatter, and Badges
- Compatible with all core apps (Purchase, Sales, Accounting, Inventory, Contacts, Settings)
- Compatible with all custom modules in customaddons
- Easy to install, disable, or uninstall with zero modifications to business logic or core files.
    """,
    'author': 'Universal Dist',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web._assets_primary_variables': [
            ('before', 'web/static/src/scss/primary_variables.scss', 'universal_dark_theme/static/src/scss/primary_variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('before', 'web/static/src/scss/bootstrap_overridden.scss', 'universal_dark_theme/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_backend': [
            'universal_dark_theme/static/src/scss/variables.scss',
            'universal_dark_theme/static/src/scss/base.scss',
            'universal_dark_theme/static/src/scss/navbar.scss',
            'universal_dark_theme/static/src/scss/control_panel.scss',
            'universal_dark_theme/static/src/scss/views_list.scss',
            'universal_dark_theme/static/src/scss/views_form.scss',
            'universal_dark_theme/static/src/scss/views_kanban.scss',
            'universal_dark_theme/static/src/scss/views_pivot_graph.scss',
            'universal_dark_theme/static/src/scss/components.scss',
            'universal_dark_theme/static/src/scss/datetimepicker.scss',
            'universal_dark_theme/static/src/scss/chatter.scss',
            'universal_dark_theme/static/src/scss/custom_addons_compat.scss',
        ],
        'web.assets_web_dark': [
            'universal_dark_theme/static/src/scss/variables.scss',
            'universal_dark_theme/static/src/scss/base.scss',
            'universal_dark_theme/static/src/scss/navbar.scss',
            'universal_dark_theme/static/src/scss/control_panel.scss',
            'universal_dark_theme/static/src/scss/views_list.scss',
            'universal_dark_theme/static/src/scss/views_form.scss',
            'universal_dark_theme/static/src/scss/views_kanban.scss',
            'universal_dark_theme/static/src/scss/views_pivot_graph.scss',
            'universal_dark_theme/static/src/scss/components.scss',
            'universal_dark_theme/static/src/scss/datetimepicker.scss',
            'universal_dark_theme/static/src/scss/chatter.scss',
            'universal_dark_theme/static/src/scss/custom_addons_compat.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
