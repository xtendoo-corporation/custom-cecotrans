# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cecotrans_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cecotrans invoice partner",
        readonly=False,
        config_parameter='cecotrans_invoice_import.cecotrans_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=',True)]",
        check_company=True,
    )
