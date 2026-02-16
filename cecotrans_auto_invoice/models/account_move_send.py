from odoo import models, api, _


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _get_move_constraints(self, move):
        constraints = super()._get_move_constraints(move)
        print(
            f"AutoInvoice: Checking constraints for move {move.id} ({move.move_type}). Original constraints: {constraints.keys()}"
        )
        # Allow sending emails for Vendor Bills (Self-Billing)
        if move.move_type == "in_invoice" and "not_sale_document" in constraints:
            print(
                f"AutoInvoice: Removing not_sale_document constraint for move {move.id}"
            )
            del constraints["not_sale_document"]
        return constraints
