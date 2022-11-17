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
        partner_id = self.env["ir.config_parameter"].sudo().get_param("cecotrans_invoice_import.cecotrans_partner_id")
        if not partner_id:
            raise ValidationError(
                _("Please select a partner to make invoice")
            )
        partner_id = self.env['res.partner'].sudo().browse(int(partner_id)).exists()
        try:
            decoded_data = base64.decodebytes(import_file)
            book = xlrd.open_workbook(file_contents=decoded_data)
            self.create_invoice(partner_id, book, 1)  # Sevilla resumen
            self.create_invoice(partner_id, book, 4)  # Huelva resumen
            self.create_invoice(partner_id, book, 7)  # Pto. Real resumen
            self.create_invoice(partner_id, book, 10)  # Jerez resumen
            self.create_invoice(partner_id, book, 13)  # Madrid resumen
            self.create_invoice(partner_id, book, 16)  # Burgos resumen
        except xlrd.XLRDError:
            raise ValidationError(
                _("Invalid file style, only .xls or .xlsx file allowed")
            )
        except Exception as e:
            raise e

    @api.model
    def create_invoice(self, partner_id, book, index_sheet):
        print("*" * 80)
        invoice_data = self._import_sheet(book, index_sheet)
        if invoice_data:
            invoice = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner_id,
                    "date": fields.Date.today(),
                    "invoice_date": fields.Date.today(),
                    "currency_id": self.env.company.currency_id,
                }
            )
            for line in invoice_data["lines"]:
                products = self.env["product.template"].search(
                    [
                        ("name", "=", line["route"]),
                    ],
                    limit=1,
                )
                if products:

                    taxes = products[0].taxes_id.filtered(
                                lambda tax: tax.company_id == invoice.company_id
                    )

                    print("taxes:", taxes)

                    invoice_line = self.env["account.move.line"].create(
                        {
                            "move_id": invoice.id,
                            "product_id": products[0].id,
                            "name": products[0].description_sale,
                            "account_id": products[0].property_account_income_id.id,
                            "price_unit": line["price"],
                        }
                    )
                    # invoice_line._onchange_product_id()

                    invoice_line._onchange_price_subtotal()
                    invoice_line._onchange_mark_recompute_taxes()

            print("invoice", invoice)

        print("invoice data lines", invoice_data["lines"])
        print("invoice data gas", invoice_data["gas"])
        print("*" * 80)

    @api.model
    def _import_sheet(self, book, index_sheet):
        lines = []
        sheet = book.sheet_by_index(index_sheet)
        for row in range(3, sheet.nrows):
            lines.append({"route": "{:.0f}".format(sheet.cell_value(row, 1)), "price": sheet.cell_value(row, 3)})
        gas = sheet.cell_value(3, 6)
        return {"lines": lines, "gas": gas}
