from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    vendor_bill_import_journal_id = fields.Many2one(
        related="company_id.vendor_bill_import_journal_id",
        string="Diario por defecto",
        readonly=False,
    )
