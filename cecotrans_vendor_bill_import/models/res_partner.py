import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_autofactura_prefix(self):
        return "CE"

    @api.model
    def _default_autofactura_next_ref(self):
        return self._format_autofactura_ref(
            self._default_autofactura_prefix(),
            fields.Date.context_today(self).year,
            1,
        )

    prefijo = fields.Char(
        string="Prefijo",
        copy=False,
        default=lambda self: self._default_autofactura_prefix(),
        help="Prefijo usado para generar la referencia de autofactura del proveedor.",
    )

    autofactura_next_ref = fields.Char(
        string="Próxima autofactura",
        copy=False,
        default=lambda self: self._default_autofactura_next_ref(),
        help="Siguiente número que se utilizará al crear una autofactura en el diario Autofacturas para este proveedor.",
    )

    @api.model
    def _normalize_autofactura_prefix(self, prefix):
        normalized = (prefix or "").strip().upper()
        return normalized or self._default_autofactura_prefix()

    @api.model
    def _format_autofactura_ref(self, prefix, year, number):
        normalized_prefix = self._normalize_autofactura_prefix(prefix)
        return f"{normalized_prefix}/{int(year)}/{int(number):04d}"

    @api.model
    def _parse_autofactura_ref(self, ref):
        ref_text = (ref or "").strip()
        if not ref_text:
            return None
        match = re.fullmatch(
            r"(?P<prefix>[^/]+)/(?P<year>\d{4})/(?P<number>\d+)", ref_text
        )
        if not match:
            return None
        return {
            "prefix": self._normalize_autofactura_prefix(match.group("prefix")),
            "year": int(match.group("year")),
            "number": int(match.group("number")),
        }

    def _get_autofactura_prefix(self):
        self.ensure_one()
        return self._normalize_autofactura_prefix(self.prefijo)

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
            self._get_autofactura_prefix(),
            self._get_autofactura_year(invoice_date),
            1,
        )

    def _get_current_autofactura_ref(self, invoice_date=None):
        self.ensure_one()
        target_year = self._get_autofactura_year(invoice_date)
        target_prefix = self._get_autofactura_prefix()
        parsed_ref = self._parse_autofactura_ref(self.autofactura_next_ref)
        if (
            not parsed_ref
            or parsed_ref["year"] != target_year
            or parsed_ref["prefix"] != target_prefix
        ):
            return self._format_autofactura_ref(target_prefix, target_year, 1)
        return self._format_autofactura_ref(
            parsed_ref["prefix"], parsed_ref["year"], parsed_ref["number"]
        )

    @api.model
    def _increment_autofactura_ref(self, ref, step=1):
        parsed_ref = self._parse_autofactura_ref(ref)
        if not parsed_ref:
            raise ValidationError(
                _(
                    "La referencia de autofactura '%s' no sigue el formato PREFIJO/AÑO/0001."
                )
                % ref
            )
        return self._format_autofactura_ref(
            parsed_ref["prefix"],
            parsed_ref["year"],
            parsed_ref["number"] + step,
        )

    @api.constrains("prefijo")
    def _check_autofactura_prefix(self):
        for partner in self:
            if partner.prefijo and "/" in partner.prefijo:
                raise ValidationError(
                    _("El prefijo no puede contener el carácter '/'.")
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

    def _initialize_autofactura_prefix(self):
        for partner in self.filtered(lambda p: p.supplier_rank > 0 and not p.prefijo):
            partner.write({"prefijo": partner._default_autofactura_prefix()})

    def _sync_autofactura_next_ref_with_prefix(self):
        for partner in self.filtered(lambda p: p.supplier_rank > 0):
            parsed_ref = partner._parse_autofactura_ref(partner.autofactura_next_ref)
            current_ref = partner._get_current_autofactura_ref()
            if not parsed_ref or parsed_ref["prefix"] != partner._get_autofactura_prefix():
                partner.write({"autofactura_next_ref": current_ref})

    @api.model
    def _initialize_missing_autofactura_next_ref(self):
        self.search(
            [("supplier_rank", ">", 0), ("autofactura_next_ref", "=", False)]
        )._initialize_autofactura_next_ref()
        return True

    @api.model
    def _initialize_missing_autofactura_prefix(self):
        self.search([("supplier_rank", ">", 0), ("prefijo", "=", False)])._initialize_autofactura_prefix()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            normalized_vals = dict(vals)
            if "prefijo" in normalized_vals:
                normalized_vals["prefijo"] = self._normalize_autofactura_prefix(
                    normalized_vals.get("prefijo")
                )
            normalized_vals_list.append(normalized_vals)
        partners = super().create(normalized_vals_list)
        for partner in partners:
            partner._initialize_autofactura_prefix()
            partner._initialize_autofactura_next_ref()
        return partners

    def write(self, vals):
        vals = dict(vals)
        if "prefijo" in vals:
            vals["prefijo"] = self._normalize_autofactura_prefix(vals.get("prefijo"))
        result = super().write(vals)
        self._initialize_autofactura_prefix()
        self._initialize_autofactura_next_ref()
        if "prefijo" in vals:
            self._sync_autofactura_next_ref_with_prefix()
        return result


