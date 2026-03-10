from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        """Interceptar create para asignar name = ref en auto_invoice
        ANTES de que Odoo lo compute con _compute_name."""
        for vals in vals_list:
            if vals.get("move_type") == "in_invoice" and vals.get("ref"):
                partner = self.env["res.partner"].browse(vals.get("partner_id"))
                if partner.auto_invoice:
                    vals["name"] = vals["ref"]
        return super().create(vals_list)

    def write(self, vals):
        """Interceptar write para forzar name = ref en auto_invoice
        cuando cambia el state a posted (al confirmar la factura)."""
        result = super().write(vals)
        # Si se ha publicado, forzar name = ref para las auto_invoice
        if vals.get("state") == "posted":
            for move in self:
                if (
                    move.move_type == "in_invoice"
                    and move.partner_id.auto_invoice
                    and move.ref
                    and move.name != move.ref
                ):
                    # Bypass del ORM para evitar recursión y recompute
                    self.env.cr.execute(
                        "UPDATE account_move SET name = %s WHERE id = %s",
                        (move.ref, move.id),
                    )
                    move.invalidate_recordset(["name"])
        return result

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
            # Set Journal from settings
            journal = self.env.company.vendor_bill_import_journal_id
            if journal:
                self.journal_id = journal

            # Use the same logic as import wizard: ir.sequence by partner name
            sequence_code = self.partner_id.name
            partner_sequence = self.env["ir.sequence"].search(
                [("code", "=", sequence_code)], limit=1
            )

            # Create sequence if it doesn't exist (same logic as wizard)
            if not partner_sequence:
                partner_sequence = self.env["ir.sequence"].create(
                    {
                        "name": self.partner_id.name,
                        "code": sequence_code,
                        "implementation": "no_gap",
                        "prefix": "CE/%(year)s/",
                        "padding": 5,
                        "number_increment": 1,
                        "number_next_actual": 1,
                        "company_id": self.company_id.id,
                    }
                )

            # Ensure prefix format matches wizard
            if partner_sequence.prefix != "CE/%(year)s/":
                partner_sequence.write({"prefix": "CE/%(year)s/"})

            # Get next reference
            # Note: next_by_code commits the transaction, so the number is consumed.
            # However, since this is an onchange, it might be consumed even if the user doesn't save.
            # But the user specifically asked to copy the wizard logic.
            new_ref = partner_sequence.next_by_id()

            self.ref = new_ref
            self.name = new_ref
