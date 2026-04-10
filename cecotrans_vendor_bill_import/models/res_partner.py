import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_autofactura_next_ref(self):
        return self._format_autofactura_ref(fields.Date.context_today(self).year, 1)

    autofactura_next_ref = fields.Char(
        string="Próxima autofactura",
        copy=False,
        default=lambda self: self._default_autofactura_next_ref(),
        help="Siguiente número que se utilizará al crear una autofactura en el diario Autofacturas para este proveedor.",
    )

    @api.model
    def _format_autofactura_ref(self, year, number):
        return f"CE/{int(year)}/{int(number):04d}"

    @api.model
    def _parse_autofactura_ref(self, ref):
        if not ref:
            return None
        match = re.fullmatch(r"CE/(?P<year>\d{4})/(?P<number>\d+)", ref.strip())
        if not match:
            return None
        return {
            "year": int(match.group("year")),
            "number": int(match.group("number")),
        }

    @api.model
    def _get_autofactura_year(self, invoice_date=None):
        target_date = (
            fields.Date.to_date(invoice_date)
            if invoice_date
            else fields.Date.context_today(self)
        )
        return target_date.year

    def _get_initial_autofactura_ref(self, invoice_date=None):
        self.ensure_one()
        return self._format_autofactura_ref(
            self._get_autofactura_year(invoice_date),
            1,
        )

    def _get_current_autofactura_ref(self, invoice_date=None):
        self.ensure_one()
        target_year = self._get_autofactura_year(invoice_date)
        parsed_ref = self._parse_autofactura_ref(self.autofactura_next_ref)
        if not parsed_ref or parsed_ref["year"] != target_year:
            return self._format_autofactura_ref(target_year, 1)
        return self._format_autofactura_ref(
            parsed_ref["year"], parsed_ref["number"]
        )

    @api.model
    def _increment_autofactura_ref(self, ref, step=1):
        parsed_ref = self._parse_autofactura_ref(ref)
        if not parsed_ref:
            raise ValidationError(
                _(
                    "La referencia de autofactura '%s' no sigue el formato CE/AÑO/0001."
                )
                % ref
            )
        return self._format_autofactura_ref(
            parsed_ref["year"], parsed_ref["number"] + step
        )

    def _advance_autofactura_ref(self, invoice_date=None, step=1):
        for partner in self:
            current_ref = partner._get_current_autofactura_ref(invoice_date)
            partner.write(
                {
                    "autofactura_next_ref": partner._increment_autofactura_ref(
                        current_ref, step=step
                    )
                }
            )
        return True

    def _advance_autofactura_ref_from_used_ref(self, used_ref, step=1):
        self.ensure_one()
        self.write(
            {
                "autofactura_next_ref": self._increment_autofactura_ref(
                    used_ref, step=step
                )
            }
        )
        return True

    def _initialize_autofactura_next_ref(self):
        for partner in self.filtered(
            lambda p: p.supplier_rank > 0 and not p.autofactura_next_ref
        ):
            partner.write(
                {
                    "autofactura_next_ref": partner._get_initial_autofactura_ref()
                }
            )

    @api.model
    def _initialize_missing_autofactura_next_ref(self):
        self.search(
            [("supplier_rank", ">", 0), ("autofactura_next_ref", "=", False)]
        )._initialize_autofactura_next_ref()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._initialize_autofactura_next_ref()
        return partners

    def write(self, vals):
        result = super().write(vals)
        self._initialize_autofactura_next_ref()
        return result


