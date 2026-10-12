from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _search_display_name(self, operator, value):
        """Product Template ko sirf Internal Reference se search karo."""
        if value and operator not in ('not ilike', 'not like', '!=', 'not in'):
            return [('product_variant_ids.default_code', operator, value)]
        return super()._search_display_name(operator, value)
