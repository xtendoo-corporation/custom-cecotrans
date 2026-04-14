import logging
import base64
from datetime import datetime
import xlrd
from odoo import _, fields, api, models
from odoo.exceptions import ValidationError

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
        """Process the file chosen in the wizard, create bank statement(s) and go to reconciliation."""
        self.ensure_one()
        if self.import_file:
            self._import_record_data(self.import_file)
            # for invoice in invoice_create_ids:
            #     invoice.send_vendor_bill_mail_template()
            return self._action_open_autofacturas_draft_vendor_bills()
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
                if row != sh.nrows - 1:
                    nif_next = sh.cell_value(rowx=row + 1, colx=1)
                else:
                    nif_next = None
                if nif == nif_next:
                    lines_num.append(row)

                else:
                    lines_num.append(row)
                    partner_id = (
                        self.env["res.partner"].search([("vat", "=", nif)]).exists()
                    )
                    if not partner_id:
                        raise ValidationError(
                            _(
                                "No se ha encontrado ningún proveedor con NIF %s."
                            )
                            % nif
                        )
                    vendor_bill_date_cell = sh.cell_value(row, 3)
                    year, month, day, hour, minute, second = xlrd.xldate_as_tuple(
                        vendor_bill_date_cell, book.datemode
                    )
                    vendor_bill_date = datetime(year, month, day)

                    try:
                        invoice_create = self.create_vendor_bill(
                            partner_id, nif, sh, lines_num, vendor_bill_date
                        )
                        if invoice_create:
                            invoice_create_ids.append(invoice_create)
                    except xlrd.XLRDError:
                        raise ValidationError(
                            _("Invalid file style, only .xls or .xlsx file allowed")
                        )
                    except Exception as e:
                        raise e
                    lines_num = []
        return invoice_create_ids

    def _get_autofacturas_journal(self):
        company = self.env.company
        journals = self.env["account.journal"].search(
            [
                ("name", "=", "Autofacturas"),
                ("type", "=", "purchase"),
                ("company_id", "=", company.id),
            ],
            limit=2,
        )
        if not journals:
            raise ValidationError(
                _(
                    "No se ha encontrado el diario de compras 'Autofacturas' para la compañía %s."
                )
                % company.display_name
            )
        if len(journals) > 1:
            raise ValidationError(
                _(
                    "Se han encontrado varios diarios de compras llamados 'Autofacturas' para la compañía %s. Revise la configuración."
                )
                % company.display_name
            )
        return journals

    def _get_import_product(self):
        product = self.env["product.product"].search(
            [("default_code", "=", "TRN")],
            limit=1,
        )
        if not product:
            raise ValidationError(
                _(
                    "No se ha encontrado ningún producto con referencia interna 'TRN'."
                )
            )
        return product

    def _action_open_autofacturas_draft_vendor_bills(self):
        journal = self._get_autofacturas_journal()
        return {
            "type": "ir.actions.act_window",
            "name": _("Autofacturas"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "target": "current",
            "domain": [
                ("move_type", "=", "in_invoice"),
                ("journal_id", "=", journal.id),
                ("state", "=", "draft"),
            ],
            "context": {
                "default_move_type": "in_invoice",
                "default_journal_id": journal.id,
            },
        }

    @api.model
    def create_vendor_bill(self, partner_id, nif, sh, lines_num, vendor_bill_date):
        vendor_bill_lines = self._prepare_vendor_bill_lines(sh, lines_num, partner_id)
        ref = self.get_vendor_bill_ref(partner_id, vendor_bill_date)
        invoice_hash = self._prepare_vendor_bill(
            partner_id, vendor_bill_lines, ref, vendor_bill_date
        )
        if invoice_hash:
            invoice_create = self.env["account.move"].create(invoice_hash)
            partner_id._advance_autofactura_ref_from_used_ref(ref)
            # No publicar automáticamente: dejar la factura en borrador para revisión/manual posting
            # invoice_create.action_post()  # removido intencionalmente
            return invoice_create
        return

    def _prepare_vendor_bill_lines(self, sh, lines, partner_id):
        vendor_bill_lines = []
        product = self._get_import_product()
        for line in lines:
            concept = sh.cell_value(rowx=line, colx=4)
            line_description = str(concept).strip() if concept is not None else ""
            taxes = self.env["account.fiscal.position"]
            fiscal_position = partner_id.property_account_position_id
            if fiscal_position:
                taxes = self.env["account.fiscal.position"].search(
                    [("name", "=", fiscal_position.name)], limit=1
                )
            if taxes:
                taxes_ids = taxes.tax_ids.filtered(
                    lambda tax: tax.company_id == self.env.user.company_id
                    and tax.tax_src_id == product.supplier_taxes_id
                ).tax_dest_id
            else:
                taxes_ids = product.supplier_taxes_id
            price_unit = sh.cell_value(rowx=line, colx=6)
            quantity = sh.cell_value(rowx=line, colx=5)
            vendor_bill_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": line_description,
                        "account_id": product.property_account_income_id.id,
                        "price_unit": price_unit,
                        "tax_ids": [(6, 0, taxes_ids.ids)],
                        "quantity": quantity,
                    },
                )
            )
        if not vendor_bill_lines:
            raise ValidationError(
                _("No lines get from Excel file to import in this invoice.")
            )
        return vendor_bill_lines

    def _prepare_vendor_bill(
        self, partner_id, vendor_bill_lines, ref, vendor_bill_date
    ):
        self.ensure_one()
        journal = self._get_autofacturas_journal()
        invoice_vals = {
            "move_type": "in_invoice",
            "ref": ref,
            "partner_id": partner_id.id,
            "journal_id": journal.id,  # company comes from the journal
            "date": vendor_bill_date,
            "invoice_date": vendor_bill_date,
            "invoice_line_ids": vendor_bill_lines,
            "state": "draft",
        }
        return invoice_vals

    def get_vendor_bill_ref(self, partner_id, vendor_bill_date):
        return partner_id._get_current_autofactura_ref(vendor_bill_date)
