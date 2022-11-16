import logging
import base64
import uuid
from ast import literal_eval
from datetime import date, datetime as dt
from io import BytesIO

import xlrd
import xlwt

from odoo import _, fields, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class CecotransInvoiceImport(models.TransientModel):
    _name = "cecotrans.invoice.import"
    _description = "Cecotrans Invoice Import"

    import_file = fields.Binary(string="Import File (*.xlsx)")

    webservice_backend_id = fields.Many2one("webservice.backend")

    def action_import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()
        if self.import_file:
            self._import_record_data(self.import_file)
        else:
            raise ValidationError(_("Please select Excel file to import"))

    @api.model
    def _import_record_data(self, import_file):
        try:
            decoded_data = base64.decodebytes(import_file)
            book = xlrd.open_workbook(file_contents=decoded_data)
            self._import_sheet(book, 1)  # Sevilla resumen
            self._import_sheet(book, 4)  # Huelva resumen
            self._import_sheet(book, 7)  # Pto. Real resumen
            self._import_sheet(book, 10)  # Jerez resumen
            self._import_sheet(book, 13)  # Madrid resumen
            self._import_sheet(book, 16)  # Burgos resumen
        except xlrd.XLRDError:
            raise ValidationError(
                _("Invalid file style, only .xls or .xlsx file allowed")
            )
        except Exception as e:
            raise e

    @api.model
    def _import_sheet(self, book, sheet):
        lines = []
        sheet = book.sheet_by_index(sheet)
        print("*" * 80)
        for row in range(3, sheet.nrows):
            lines.append({"route": "{:.0f}".format(sheet.cell_value(row, 1)), "price": sheet.cell_value(row, 3)})
        gas = sheet.cell_value(3, 6)
        print(lines)
        print(gas)
        print("*" * 80)
        return {"lines": lines, "gas": gas}
