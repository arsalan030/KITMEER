from odoo import models, fields, api


class ProductDefaultCode(models.Model):
    _name = 'product.default.code'
    _description = 'Product by Default Code'
    _inherit = 'product.product'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None, name_get_uid=None):
        """Sirf default_code se search karo."""
        domain = domain or []
        if name:
            # Default code se dhoondo
            product_ids = self.env['product.product']._search([
                ('default_code', operator, name)
            ], limit=limit)
            if product_ids:
                return product_ids
            # Agar default_code se nahi mila, to kuch return na karo
            return []
        return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order, name_get_uid=name_get_uid)