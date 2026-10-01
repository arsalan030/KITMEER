from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_default_code = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        readonly=True,
    )
    product_description = fields.Text(
        string='Description',
        related='name',
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
    fixed_amount = fields.Float(
        string='Fixed Amount',
        digits='Product Price',
    )
    discount_mode = fields.Selection(
        [('percent', 'Percent'), ('amount', 'Amount')],
        string='Discount Mode',
        copy=True,
    )

    @api.depends('product_id')
    def _compute_unit_quantity(self):
        for line in self:
            line.unit_quantity = 0.0
            product = line.product_id
            if not product:
                continue
            try:
                if product.uom_id:
                    line.unit_quantity = product.uom_id.factor or 0.0
                elif product.packaging_ids:
                    line.unit_quantity = product.packaging_ids[0].qty
                elif product.product_tmpl_id.packaging_ids:
                    line.unit_quantity = product.product_tmpl_id.packaging_ids[0].qty
            except Exception:
                line.unit_quantity = 0.0

    @api.onchange('discount')
    def _onchange_discount_set_fixed(self):
        for line in self:
            # Amount se convert hua discount ho to mode na badlein
            if line.discount_mode == 'amount':
                continue
            line.discount_mode = 'percent' if line.discount else False
            line.fixed_amount = (line.price_unit or 0.0) * (line.discount or 0.0) / 100.0

    @api.onchange('fixed_amount')
    def _onchange_fixed_amount_set_discount(self):
        for line in self:
            # Percent mode me amount readonly hai
            if line.discount_mode == 'percent':
                continue
            if line.fixed_amount:
                line.discount_mode = 'amount'
                price = line.price_unit or 0.0
                line.discount = min(line.fixed_amount / price * 100.0, 100.0) if price else 0.0
            else:
                line.discount_mode = False
                line.discount = 0.0

    @api.onchange('price_unit')
    def _onchange_price_unit_sync_discount(self):
        for line in self:
            price = line.price_unit or 0.0
            if line.discount_mode == 'amount':
                # Amount wahi rahe, percent dobara calculate ho
                line.discount = min((line.fixed_amount or 0.0) / price * 100.0, 100.0) if price else 0.0
            else:
                line.fixed_amount = price * (line.discount or 0.0) / 100.0