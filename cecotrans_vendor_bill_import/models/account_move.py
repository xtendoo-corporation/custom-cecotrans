# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    def send_vendor_bill_mail_template(self):
        template = self.env.ref('cecotrans_vendor_bill_import.example_email_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        datetime.now()
        display_msg = _("Factura enviada el %s a las %s", datetime.now().strftime("%d/%m/%Y"), datetime.now().strftime("%H:%M"))
        self.message_post(body=display_msg)
