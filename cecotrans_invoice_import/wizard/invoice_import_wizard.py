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
            print("*"*80)
            print("Import file:", self.import_file)
            print("*"*80)
        else:
            raise ValidationError(_("Please select Excel file to import"))

    def web_service_get(self):
        result = self.webservice_backend_id.call("get")

        print("*"*80)
        print("Result:", result)
        print("*"*80)



        # with self.assertRaises(exceptions.ConnectionError):
        #     self.webservice_backend_id.call("get")

