from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    product_default_code = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        readonly=True,
    )
    product_description = fields.Text(
        string='Description',
        related='description_picking',
        readonly=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
    )
    unit_quantity = fields.Float(
        string='Unit Quantity',
        compute='_compute_unit_quantity',
        store=False,
        readonly=True,
    )
    product_amount = fields.Float(
        string='Product Amount',
        compute='_compute_product_amount',
        digits='Product Price',
        store=False,
        readonly=True,
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
        default=0.0,
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        digits='Product Price',
        store=False,
        readonly=True,
    )

    @api.depends('product_id')
    def _compute_unit_quantity(self):
        for line in self:
            line.unit_quantity = 0.0
            product = line.product_id
            if not product:
                continue
            try:
                if product.packaging_ids:
                    line.unit_quantity = product.packaging_ids[0].qty
                elif product.product_tmpl_id.packaging_ids:
                    line.unit_quantity = product.product_tmpl_id.packaging_ids[0].qty
            except Exception:
                line.unit_quantity = 0.0

    @api.depends('product_id', 'price_unit')
    def _compute_product_amount(self):
        for move in self:
            move.product_amount = (
                move.price_unit
                or move.product_id.with_company(move.company_id).standard_price
                or 0.0
            )

    @api.depends('price_unit', 'product_uom_qty')
    def _compute_total_amount(self):
        for move in self:
            move.total_amount = (move.price_unit or 0.0) * (move.product_uom_qty or 0.0)