from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_default_code = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        readonly=True
    )
    product_description = fields.Text(
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
    fixed_amount = fields.Float(
        string='Fixed Amount',
        compute='_compute_fixed_amount',
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
                    # Odoo 19: UoM se packaging quantity
                    if hasattr(product, 'uom_id') and product.uom_id:
                        line.unit_quantity = product.uom_id.factor or 0.0
                    # Purana tareeqa: packaging_ids
                    elif hasattr(product, 'packaging_ids') and product.packaging_ids:
                        line.unit_quantity = product.packaging_ids[0].qty
                    elif hasattr(product, 'product_tmpl_id') and hasattr(product.product_tmpl_id,
                                                                         'packaging_ids') and product.product_tmpl_id.packaging_ids:
                        line.unit_quantity = product.product_tmpl_id.packaging_ids[0].qty
                except Exception:
                    line.unit_quantity = 0.0

    @api.depends('price_unit', 'discount')
    def _compute_fixed_amount(self):
        for line in self:
            price = line.price_unit or 0.0
            discount = line.discount or 0.0
            # Discount ki value amount mein (2400 * 10 / 100 = 240)
            line.fixed_amount = price * discount / 100.0