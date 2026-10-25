"""Duplicate protection for banks whose statements have no transaction ID column.

Each statement line gets an ID built from its date, amount, description and
reference, plus a counter for identical lines on the same day. Importing a file
that overlaps an earlier one then skips the lines that are already in Odoo.
"""
import hashlib
from collections import Counter
from datetime import datetime


def line_fingerprint(date, amount, payment_ref, ref):
    if isinstance(date, datetime):
        date = date.date()
    raw = "|".join(
        [
            date.isoformat(),
            f"{float(amount):.2f}",
            (payment_ref or "").strip(),
            str(ref or "").strip(),
        ]
    )
    return "fp-" + hashlib.sha1(raw.encode()).hexdigest()[:20]


def numbered_fingerprints(lines):
    """Yield (line, fingerprint) for (date, amount, payment_ref, ref, line) tuples,
    numbering identical lines 1, 2, 3... in the order given."""
    seen = Counter()
    for date, amount, payment_ref, ref, line in lines:
        key = line_fingerprint(date, amount, payment_ref, ref)
        seen[key] += 1
        yield line, f"{key}-{seen[key]}"
