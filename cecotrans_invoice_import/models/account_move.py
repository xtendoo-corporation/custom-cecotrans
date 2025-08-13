from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_default_journal_id(self):
        """Return the default journal for invoices"""
        move_type = self._context.get('default_move_type', 'entry')
        if move_type in ('out_invoice', 'out_refund', 'out_receipt'):
            journal_type = 'sale'
        elif move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            journal_type = 'purchase'
        else:
            journal_type = 'general'

        company_id = self._context.get('default_company_id', self.env.company.id)
        domain = [('type', '=', journal_type), ('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)
