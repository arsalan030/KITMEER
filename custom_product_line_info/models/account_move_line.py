from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_default_code = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        readonly=True
    )
    product_description = fields.Char(
        string='Description',
        related='name',
        readonly=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location'
    )
    unit_quantity = fields.Float(
        string='Unit Quantity',
        compute='_compute_unit_quantity',
        store=False,
        readonly=True
    )

    @api.depends('product_id')
    def _compute_unit_quantity(self):
        for line in self:
            line.unit_quantity = 0.0
            if line.product_id:
                product = line.product_id
                try:
                    if hasattr(product, 'packaging_ids') and product.packaging_ids:
                        line.unit_quantity = product.packaging_ids[0].qty
                    elif hasattr(product, 'product_tmpl_id') and hasattr(product.product_tmpl_id, 'packaging_ids') and product.product_tmpl_id.packaging_ids:
                        line.unit_quantity = product.product_tmpl_id.packaging_ids[0].qty
                except Exception:
                    line.unit_quantity = 0.0