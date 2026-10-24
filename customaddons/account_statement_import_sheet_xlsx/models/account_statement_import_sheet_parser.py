import io
import logging
from datetime import date, datetime

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None
    _logger.warning("openpyxl is not installed: .xlsx statements cannot be imported")

# .xlsx files are zip archives
XLSX_MAGIC = b"PK\x03\x04"
NOT_A_DATE_CELL = 1  # anything other than xlrd.XL_CELL_DATE (3)


class _XlsxSheet:
    """Holds the sheet's rows behind the small part of the xlrd API the OCA parser uses.

    Date cells are returned as datetime objects directly, so the parser skips
    its xlrd date conversion and uses them as-is.
    """

    def __init__(self, rows):
        self.rows = rows
        self.nrows = len(rows)

    def row_values(self, row):
        return self.rows[row]

    def row_len(self, row):
        return len(self.rows[row])

    def cell_type(self, row, col):
        return NOT_A_DATE_CELL

    def cell_value(self, row, col):
        return self.rows[row][col]


class _XlsxBook:
    datemode = 0


class _MappingOverride:
    """A mapping record with a few values replaced, without writing to the database."""

    def __init__(self, mapping, **overrides):
        self._mapping = mapping
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._mapping, name)

    def __getitem__(self, name):
        return self.__getattr__(name)


def _clean(value):
    if value is None:
        return ""
    # Whole numbers become text so references stay "445566" (not "445566.0");
    # the parser still reads text amounts as numbers.
    if isinstance(value, (bool, int)):
        return str(value)
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        return value.strip()
    return value


def _as_date(value, timestamp_format):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value, timestamp_format)
        except ValueError:
            return None
    return None


def _normalize(name):
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    def _get_column_indexes(self, header, column_name, mapping):
        """Match column names ignoring case, spaces and punctuation, and say which
        columns the file has when one is missing."""
        try:
            return super()._get_column_indexes(header, column_name, mapping)
        except ValueError:
            pass
        normalized_header = [_normalize(title) for title in header]
        indexes = []
        for wanted in (mapping[column_name] or "").split(","):
            if not wanted.strip():
                continue
            try:
                indexes.append(normalized_header.index(_normalize(wanted)))
            except ValueError:
                raise UserError(
                    _(
                        "Column '%(wanted)s' was not found in the file.\n"
                        "Columns in the file: %(found)s",
                        wanted=wanted.strip(),
                        found=", ".join(title for title in header if title),
                    )
                ) from None
        return indexes

    def _parse_lines(self, mapping, data_file, currency_code):
        if not data_file.startswith(XLSX_MAGIC):
            return super()._parse_lines(mapping, data_file, currency_code)
        if openpyxl is None:
            raise UserError(_("Install the Python library 'openpyxl' to import .xlsx files."))
        try:
            workbook = openpyxl.load_workbook(
                io.BytesIO(data_file), read_only=True, data_only=True
            )
        except Exception as err:
            raise UserError(_("Could not read the .xlsx file: %s", err)) from err
        rows = [
            [_clean(value) for value in row]
            for row in workbook.worksheets[0].iter_rows(values_only=True)
        ]
        workbook.close()

        rows, mapping = self._xlsx_keep_transaction_rows(rows, mapping)

        # Same steps as the OCA parser after it opens a workbook
        csv_or_xlsx = (_XlsxBook(), _XlsxSheet(rows))
        header = self.parse_header(csv_or_xlsx, mapping)
        columns = {
            column_name: self._get_column_indexes(header, column_name, mapping)
            for column_name in self._get_column_names()
        }
        return self._parse_rows(mapping, currency_code, (csv_or_xlsx, data_file), columns)

    def _xlsx_keep_transaction_rows(self, rows, mapping):
        """Find the column-title row by the date column's name, and keep only the
        rows below it whose date cell holds a valid date.

        Bank statements carry address lines above the table and disclaimers,
        summaries or separator rows (*****) around it, and their number changes
        between statements. This makes the header/footer skip counts unnecessary.
        Falls back to the mapping's skip counts when the date column isn't found.
        """
        date_column = (mapping.timestamp_column or "").strip()
        if mapping.no_header or not date_column or "," in date_column:
            return rows, mapping
        wanted = _normalize(date_column)
        offset = mapping.offset_column or 0
        header_index = date_index = None
        for i, row in enumerate(rows):
            titles = [_normalize(cell) for cell in row]
            if wanted in titles[offset:]:
                header_index, date_index = i, titles.index(wanted, offset)
                break
        if header_index is None:
            return rows, mapping
        header = rows[header_index]

        transactions = []
        for row in rows[header_index + 1 :]:
            value = row[date_index] if date_index < len(row) else ""
            timestamp = _as_date(value, mapping.timestamp_format)
            if timestamp:
                row = list(row)
                row[date_index] = timestamp
                transactions.append(row)
        mapping = _MappingOverride(
            mapping, header_lines_skip_count=1, footer_lines_skip_count=0
        )
        return [header] + transactions, mapping
