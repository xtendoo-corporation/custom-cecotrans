from odoo import models, fields, api
from odoo.tools.misc import get_lang


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        for invoice in self:
            print("FINALIZADO")
            invoice.action_send_and_print()
            # wizard.send_and_print_action()
        return invoice.action_send_and_print()
