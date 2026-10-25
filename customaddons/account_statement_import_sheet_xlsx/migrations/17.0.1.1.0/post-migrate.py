"""Add fingerprint IDs to statement lines imported before duplicate protection
existed, so re-importing those transactions skips them."""
from odoo import SUPERUSER_ID, api

from odoo.addons.account_statement_import_sheet_xlsx.models.fingerprint import (
    numbered_fingerprints,
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    journals = env["account.journal"].search(
        [("type", "=", "bank"), ("default_sheet_mapping_id", "!=", False)]
    )
    for journal in journals:
        # Same prefix the importer adds: "<account number>-<journal id>-"
        acc_number = journal._sanitize_bank_account_number(
            journal.bank_account_id.acc_number
        )
        prefix = (acc_number and acc_number + "-" or "") + str(journal.id) + "-"
        lines = env["account.bank.statement.line"].search(
            [("journal_id", "=", journal.id), ("unique_import_id", "=", False)],
            order="date, statement_id, sequence, id",
        )
        rows = [(l.date, l.amount, l.payment_ref, l.ref, l) for l in lines]
        for line, import_id in numbered_fingerprints(rows):
            cr.execute(
                "UPDATE account_bank_statement_line SET unique_import_id = %s "
                "WHERE id = %s AND NOT EXISTS ("
                "  SELECT 1 FROM account_bank_statement_line WHERE unique_import_id = %s)",
                (prefix + import_id, line.id, prefix + import_id),
            )
