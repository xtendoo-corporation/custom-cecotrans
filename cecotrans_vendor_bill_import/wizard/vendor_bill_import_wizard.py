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
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class CecotransVendorBillImport(models.TransientModel):
    _name = "cecotrans.vendor.bill.import"
    _description = "Cecotrans Invoice Import"

    import_file = fields.Binary(string="Import File (*.xlsx)")

    def action_import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()
        if self.import_file:
            invoice_create_ids = self._import_record_data(self.import_file)
            for invoice in invoice_create_ids:
                invoice.send_vendor_bill_mail_template()
        else:
            raise ValidationError(_("Please select Excel file to import"))

    @api.model
    def _import_record_data(self, import_file):
        decoded_data = base64.decodebytes(import_file)
        book = xlrd.open_workbook(file_contents=decoded_data)
        sh = book.sheet_by_index(0)
        lines_num = []
        invoice_create_ids = []
        for row in range(sh.nrows):
            if row != 0:
                nif = sh.cell_value(rowx=row, colx=1)
                if row != sh.nrows -1:
                    nif_next = sh.cell_value(rowx=row+1, colx=1)
                else:
                    nif_next = None
                if nif == nif_next:
                    lines_num.append(row)

                else:
                    lines_num.append(row)
                    partner_id = self.env["res.partner"].search([('vat', '=', nif)]).exists()
                    vendor_bill_date_cell = sh.cell_value(row, 3)
                    year, month, day, hour, minute, second = xlrd.xldate_as_tuple(vendor_bill_date_cell,
                                                                                  book.datemode)
                    vendor_bill_date = datetime(year, month, day)

                    try:
                        invoice_create = self.create_vendor_bill(partner_id, nif, sh, lines_num, vendor_bill_date)
                        if invoice_create:
                            invoice_create_ids.append(invoice_create)
                    except xlrd.XLRDError:
                        raise ValidationError(
                            _("Invalid file style, only .xls or .xlsx file allowed")
                        )
                    except Exception as e:
                        raise e
                    lines_num= []
        return invoice_create_ids

    @api.model
    def create_vendor_bill(self, partner_id, nif, sh, lines_num, vendor_bill_date):
        vendor_bill_lines = self._prepare_vendor_bill_lines(sh, lines_num, partner_id)
        ref = self.get_vendor_bill_ref(partner_id)
        invoice_hash = self._prepare_vendor_bill(partner_id, vendor_bill_lines, ref, vendor_bill_date)
        if invoice_hash:
            invoice_create = self.env["account.move"].create(invoice_hash)
            invoice_create._onchange_partner_id()
            invoice_create.action_post()
            return invoice_create
        return



    def _prepare_vendor_bill_lines(self, sh, lines, partner_id):
        vendor_bill_lines = []
        for line in lines:
            product_name = sh.cell_value(rowx=line, colx=4)
            if "Importe transporte" in product_name:
                product = self.env["product.template"].search([("name", "=", "Importe transporte")], limit=1)
            else:
                product = self.env["product.template"].search([("name", "=", "Clausula gasoil")], limit=1)
            if not product:
                raise ValidationError(
                    _('Product not found, %s please correct this.' % line["route"])
                )
            taxes = self.env["account.fiscal.position"].search([("name", "=", partner_id.property_account_position_id.name)], limit=1)
            if taxes:
                taxes_ids = taxes.tax_ids.filtered(lambda tax: tax.company_id == self.env.user.company_id and tax.tax_src_id == product.supplier_taxes_id).tax_dest_id
            else:
                taxes_ids = product.supplier_taxes_id
            price_unit = sh.cell_value(rowx=line, colx=6)
            quantity = sh.cell_value(rowx=line, colx=5)
            vendor_bill_lines.append(
                    {
                        "product_id": product.id,
                        "name": product_name,
                        "account_id": product.property_account_income_id.id,
                        "price_unit": price_unit,
                        "tax_ids": [(6, 0, taxes_ids.ids)],
                        "quantity": quantity,
                    }
                )
            if not vendor_bill_lines:
                raise ValidationError(
                    _('No lines get from Excel file to import in this invoice.')
                )
        return vendor_bill_lines

    def _prepare_vendor_bill(self, partner_id, vendor_bill_lines, ref, vendor_bill_date):
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='in_invoice')._get_default_journal()
        if not journal:
            raise ValidationError(
                _('Please define an accounting sales journal for the company %s (%s).', self.company_id.name,
                  self.company_id.id)
            )
        invoice_vals = {
            'move_type': 'in_invoice',
            'ref': ref,
            'partner_id': partner_id.id,
            'journal_id': journal.id,  # company comes from the journal
            "date": vendor_bill_date,
            "invoice_date": vendor_bill_date,
            'invoice_line_ids': vendor_bill_lines,
        }
        return invoice_vals

    def get_vendor_bill_ref(self,partner_id):

        partner_secuence = self.env["ir.sequence"].search([("name", "=", partner_id.name)])
        if not partner_secuence:
            self.env["ir.sequence"].create({
                'name': partner_id.name,
                'code': partner_id.name,
                'implementation': 'no_gap',
                'prefix': 'FAC/VTA/%(year)s/',
                'padding': 5,
                'number_increment': 1,
                'number_next_actual': 1
            })

        ref = (
                self.env["ir.sequence"].next_by_code(partner_id.name) or "/"
            )
        return ref





