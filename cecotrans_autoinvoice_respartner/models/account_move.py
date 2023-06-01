from odoo import models, fields, api
from odoo.tools.misc import get_lang


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        for invoice in self:
            if invoice.partner_id.email and invoice.move_type == 'in_invoice' and invoice.partner_id.auto_invoice:
                invoice.send_email()
        return res


    def send_email(self):
        template_id = (
            self.env["mail.template"].search([("name", "=", "Factura: Enviar por correo electrónico")], limit=1).id
        )
        template = self.env["mail.template"].browse(template_id)
        template.send_mail(self.id, force_send=True)

        values = template.generate_email(self.id, ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
        body_html = values['body_html']
        doc = self.action_invoice_print()
        Attachment = self.env['ir.attachment']

        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])

        mail = self.env['mail.mail'].sudo().create(values)

        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas': attachment[1],
                'type': 'binary',
                'res_model': 'mail.message',
                'res_id': mail.mail_message_id.id,
            }
            attachment_ids.append((4, Attachment.create(attachment_data).id))
        if attachment_ids:
            mail.write({'attachment_ids': attachment_ids})







