# -*- encoding: utf-8 -*-
from datetime import datetime
import re

from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _use_autofacturas_standard_sequence(self):
        self.ensure_one()
        return (
            self.move_type == 'in_invoice'
            and self.journal_id
            and self.journal_id.type == 'purchase'
            and self.journal_id.name == 'Autofacturas'
        )

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super()._get_last_sequence_domain(relaxed=relaxed)
        if not self._use_autofacturas_standard_sequence():
            return where_string, param

        journal_code = re.escape(self.journal_id.code or '')
        param['autofacturas_sequence_regex'] = rf'^{journal_code}/\d{{4}}/\d+$'
        where_string += " AND name ~ %(autofacturas_sequence_regex)s "
        return where_string, param

    def _get_starting_sequence(self):
        if not self._use_autofacturas_standard_sequence():
            return super()._get_starting_sequence()

        move_date = self.date or self.invoice_date
        if not move_date:
            move_date = fields.Date.context_today(self)
        return f"{self.journal_id.code}/{move_date.year}/0000"


    def send_vendor_bill_mail_template(self):
        template = self.env.ref('cecotrans_vendor_bill_import.example_email_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        datetime.now()
        display_msg = _("Factura enviada el %s a las %s", datetime.now().strftime("%d/%m/%Y"), datetime.now().strftime("%H:%M"))
        self.message_post(body=display_msg)
