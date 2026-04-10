# -*- encoding: utf-8 -*-
import re
from datetime import date, datetime

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _use_autofactura_annual_sequence(self):
        self.ensure_one()
        return (
            self.move_type == 'in_invoice'
            and self.journal_id.type == 'purchase'
            and self.journal_id.name == 'Autofacturas'
        )

    def _get_autofactura_name_regex(self, monthly=False):
        self.ensure_one()
        prefix = re.escape(self.journal_id.code or '')
        if monthly:
            return rf'^{prefix}/\d{{4}}/\d{{2}}/\d+$'
        return rf'^{prefix}/\d{{4}}/\d+$'

    def _autofactura_name_requires_reset(self):
        self.ensure_one()
        return (
            (self.ref and self.name == self.ref)
            or bool(self.name and re.fullmatch(self._get_autofactura_name_regex(monthly=True), self.name))
        )

    def _get_last_sequence_domain(self, relaxed=False):
        if not self._use_autofactura_annual_sequence():
            return super()._get_last_sequence_domain(relaxed=relaxed)

        if not self.date or not self.journal_id:
            return "WHERE FALSE", {}

        where_string = "WHERE journal_id = %(journal_id)s AND name != '/' AND name ~ %(sequence_regex)s"
        param = {
            'journal_id': self.journal_id.id,
            'sequence_regex': self._get_autofactura_name_regex(),
        }

        if not relaxed:
            move_date = fields.Date.to_date(self.date)
            param['date_start'] = date(move_date.year, 1, 1)
            param['date_end'] = date(move_date.year, 12, 31)
            where_string += " AND date BETWEEN %(date_start)s AND %(date_end)s"

        return where_string, param

    def _get_starting_sequence(self):
        if not self._use_autofactura_annual_sequence():
            return super()._get_starting_sequence()

        self.ensure_one()
        move_date = self.date or self.invoice_date or fields.Date.context_today(self)
        return f"{self.journal_id.code}/{move_date.year}/0000"

    @api.model
    def _fix_autofactura_draft_names(self):
        moves = self.search([
            ('state', '=', 'draft'),
            ('move_type', '=', 'in_invoice'),
            ('journal_id.type', '=', 'purchase'),
            ('journal_id.name', '=', 'Autofacturas'),
        ])
        for move in moves.sorted(lambda m: (m.date, m.id)):
            if move._autofactura_name_requires_reset():
                move.name = False
            if not move.name or move.name == '/':
                move._set_next_sequence()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        if not self.env.context.get('reserve_autofactura_move_name'):
            return moves

        autofactura_moves = moves.filtered(
            lambda move: move.state == 'draft'
            and move.move_type == 'in_invoice'
            and move.journal_id.type == 'purchase'
            and move.journal_id.name == 'Autofacturas'
        )
        for move in autofactura_moves.sorted(lambda m: (m.date, m.id)):
            if move._autofactura_name_requires_reset():
                move.name = False
            if not move.name or move.name == '/':
                move._set_next_sequence()
        return moves

    def send_vendor_bill_mail_template(self):
        template = self.env.ref('cecotrans_vendor_bill_import.example_email_template')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
        datetime.now()
        display_msg = _("Factura enviada el %s a las %s", datetime.now().strftime("%d/%m/%Y"), datetime.now().strftime("%H:%M"))
        self.message_post(body=display_msg)
