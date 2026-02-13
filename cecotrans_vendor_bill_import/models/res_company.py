from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    vendor_bill_import_journal_id = fields.Many2one(
        "account.journal", string="Diario por defecto"
    )
