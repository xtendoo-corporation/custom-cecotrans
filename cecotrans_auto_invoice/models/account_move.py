from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_autofacturas_journal(self):
        return self.env["account.journal"].search(
            [
                ("name", "=", "Autofacturas"),
                ("type", "=", "purchase"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    @api.model
    def _is_autofacturas_journal(self, journal):
        return bool(journal and journal.type == "purchase" and journal.name == "Autofacturas")

    @api.model_create_multi
    def create(self, vals_list):
        """Asignar journal/ref de autofactura sin tocar el name,
        que debe seguir la secuencia estándar del diario."""
        pending_partner_sequences = {}
        for vals in vals_list:
            if vals.get("move_type") != "in_invoice":
                continue
            partner = self.env["res.partner"].browse(vals.get("partner_id"))
            if not partner:
                continue

            journal = self.env["account.journal"].browse(vals.get("journal_id"))
            if not journal:
                journal = self._get_autofacturas_journal()
                if journal:
                    vals["journal_id"] = journal.id

            if not self._is_autofacturas_journal(journal):
                continue

            invoice_date = vals.get("invoice_date") or vals.get("date")
            key = (partner.id, partner._get_autofactura_year(invoice_date))
            current_ref = pending_partner_sequences.get(key)
            if not current_ref:
                current_ref = partner._get_current_autofactura_ref(invoice_date)

            vals["ref"] = current_ref

            if not self.env.context.get("skip_autofactura_partner_sequence"):
                pending_partner_sequences[key] = partner._increment_autofactura_ref(
                    current_ref
                )

        moves = super().create(vals_list)

        if not self.env.context.get("skip_autofactura_partner_sequence"):
            for (partner_id, year), next_ref in pending_partner_sequences.items():
                partner = self.env["res.partner"].browse(partner_id)
                if partner.exists():
                    partner.write({"autofactura_next_ref": next_ref})

        return moves
    def _post(self, soft=True):
        res = super()._post(soft=soft)
        for invoice in self:
            if (
                invoice.partner_id.email
                and invoice.move_type == "in_invoice"
                and invoice.partner_id.auto_invoice
            ):
                invoice.send_email()
        return res

    def send_email(self):
        # Use standard Odoo logic to generate PDF and send email
        # This will also log the email in the chatter
        self.env["account.move.send"]._generate_and_send_invoices(
            self, sending_methods={"email"}
        )

    @api.onchange("partner_id")
    def _onchange_partner_id_auto_invoice(self):
        if (
            self.move_type == "in_invoice"
            and self.partner_id
            and self.partner_id.auto_invoice
        ):
            journal = self._get_autofacturas_journal()
            if journal:
                self.journal_id = journal

            new_ref = self.partner_id._get_current_autofactura_ref(
                self.invoice_date or self.date
            )

            self.ref = new_ref
