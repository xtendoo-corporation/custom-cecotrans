from odoo import models, fields, api
from odoo.tools.misc import get_lang


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        for invoice in self:
            if (
                invoice.partner_id.email
                and invoice.move_type == "in_invoice"
                and invoice.partner_id.auto_invoice
            ):
                invoice.send_email()
        return res

    def send_email(self):
        template_id = (
            self.env["mail.template"]
            .search([("name", "=", "Factura: Enviar por correo electrónico")], limit=1)
            .id
        )
        template = self.env["mail.template"].browse(template_id)
        template.send_mail(self.id, force_send=True)

        values = template.generate_email(
            self.id,
            [
                "subject",
                "body_html",
                "email_from",
                "email_to",
                "partner_to",
                "email_cc",
                "reply_to",
                "scheduled_date",
            ],
        )
        body_html = values["body_html"]
        doc = self.action_invoice_print()
        Attachment = self.env["ir.attachment"]

        attachment_ids = values.pop("attachment_ids", [])
        attachments = values.pop("attachments", [])

        mail = self.env["mail.mail"].sudo().create(values)

        for attachment in attachments:
            attachment_data = {
                "name": attachment[0],
                "datas": attachment[1],
                "type": "binary",
                "res_model": "mail.message",
                "res_id": mail.mail_message_id.id,
            }
            attachment_ids.append((4, Attachment.create(attachment_data).id))
        if attachment_ids:
            mail.write({"attachment_ids": attachment_ids})

    @api.onchange("partner_id")
    def _onchange_partner_id_auto_invoice(self):
        if (
            self.move_type == "in_invoice"
            and self.partner_id
            and self.partner_id.auto_invoice
        ):
            # Set Journal from settings
            journal = self.env.company.vendor_bill_import_journal_id
            if journal:
                self.journal_id = journal

            # Determine prefix from journal code or fallback to CE
            prefix = "CE"
            if self.journal_id and self.journal_id.code:
                prefix = self.journal_id.code

            # Calculate Reference
            current_year = fields.Date.context_today(self).year
            new_ref = False

            # Find last invoice for this partner with similar format
            last_invoice = self.env["account.move"].search(
                [
                    ("move_type", "=", "in_invoice"),
                    ("partner_id", "=", self.partner_id.id),
                    ("state", "!=", "cancel"),
                    ("ref", "like", f"{prefix}/%"),
                ],
                limit=1,
                order="date desc, id desc",
            )

            if last_invoice and last_invoice.ref:
                try:
                    parts = last_invoice.ref.split("/")
                    # Expected format: PREFIX/YYYY/XXXXX
                    if len(parts) == 3 and parts[0] == prefix:
                        year_str = parts[1]
                        seq_str = parts[2]

                        if year_str == str(current_year):
                            new_seq = int(seq_str) + 1
                            new_ref = f"{prefix}/{current_year}/{str(new_seq).zfill(5)}"
                except (ValueError, IndexError):
                    pass

            if not new_ref:
                new_ref = f"{prefix}/{current_year}/00001"

            self.ref = new_ref
