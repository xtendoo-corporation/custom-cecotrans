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
            self.create_invoice(partner_id, book, 1, 'Sevilla')  # Sevilla resumen
            self.create_invoice(partner_id, book, 4, 'Huelva')  # Huelva resumen
            self.create_invoice(partner_id, book, 7, 'Puerto Real')  # Pto. Real resumen
            self.create_invoice(partner_id, book, 10, 'Jerez')  # Jerez resumen
            self.create_invoice(partner_id, book, 13, 'Madrid')  # Madrid resumen
            self.create_invoice(partner_id, book, 16, 'Burgos')  # Burgos resumen
        except xlrd.XLRDError:
            raise ValidationError(
                _("Invalid file style, only .xls or .xlsx file allowed")
            )
        except Exception as e:
            raise e

    def _prepare_invoice_lines(self, invoice_data):
        lines = []
        for line in invoice_data['lines']:
            product = self.env["product.template"].search([("name", "=", line["route"])], limit=1)
            if not product:
                raise ValidationError(
                    _('Product not found, %s please correct this.' % line["route"])
                )
            taxes = product.taxes_id.filtered(lambda tax: tax.company_id == self.env.user.company_id)
            lines.append(
                {
                    "product_id": product.id,
                    "name": product.description_sale,
                    "account_id": product.property_account_income_id.id,
                    "price_unit": line["price"],
                    "tax_ids": [(6, 0, taxes.ids)],
                }
            )
        if not lines:
            raise ValidationError(
                _('No lines get from Excel file to import in this invoice.')
            )
        gas_product = self.env["product.template"].search([("default_code", "=", "GAS")], limit=1)
        if not gas_product:
            raise ValidationError(
                _('No Gas product found, please correct.')
            )
        lines.append(
            {
                "product_id": gas_product.id,
                "name": gas_product.description_sale,
                "account_id": gas_product.property_account_income_id.id,
                "price_unit": invoice_data['gas'],
                "tax_ids": [(6, 0, taxes.ids)],
            }
        )
        return lines

    def _prepare_invoice(self, partner_id, invoice_data, ref):
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise ValidationError(
                _('Please define an accounting sales journal for the company %s (%s).', self.company_id.name,
                  self.company_id.id)
            )
        invoice_lines = self._prepare_invoice_lines(invoice_data)
        if not invoice_lines:
            raise ValidationError(
                _('No lines to import in this invoice.')
            )
        invoice_vals = {
            'move_type': 'out_invoice',
            'ref': ref,
            'partner_id': partner_id.id,
            'journal_id': journal.id,  # company comes from the journal
            "date": fields.Date.today(),
            "invoice_date": fields.Date.today(),
            'invoice_line_ids': invoice_lines,
        }
        return invoice_vals

    @api.model
    def create_invoice(self, partner_id, book, index_sheet, ref):
        invoice_data = self._import_sheet(book, index_sheet)
        if not invoice_data:
            raise ValidationError(
                _('No invoice data getting sheet.')
            )
        invoice_hash = self._prepare_invoice(partner_id, invoice_data, ref)
        if invoice_hash:
            self.env["account.move"].create(invoice_hash)

    @api.model
    def _import_sheet(self, book, index_sheet):
        lines = []
        sheet = book.sheet_by_index(index_sheet)
        for row in range(3, sheet.nrows):
            lines.append(
                {
                    "route": "{:.0f}".format(sheet.cell_value(row, 1)),
                    "price": sheet.cell_value(row, 3),
                }
            )
        gas = sheet.cell_value(3, 6)
        return {"lines": lines, "gas": gas}
