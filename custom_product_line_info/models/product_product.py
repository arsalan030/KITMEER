from odoo import models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search_display_name(self, operator, value):
        """Sirf Internal Ref wale field me default_code se search karo."""
        if self.env.context.get('internal_ref_search') and value \
                and operator not in ('not ilike', 'not like', '!=', 'not in'):
            return [('default_code', operator, value)]
        return super()._search_display_name(operator, value)

    @api.depends_context('internal_ref_search')
    def _compute_display_name(self):
        if self.env.context.get('internal_ref_search'):
            for product in self:
                product.display_name = product.default_code or ''
            return
        return super()._compute_display_name()