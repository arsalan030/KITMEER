from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    product_default_code = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        readonly=True,
    )
    product_ref_id = fields.Many2one(
        'product.product',
        string='Internal Reference',
        compute='_compute_product_ref_id',
        inverse='_inverse_product_ref_id',
        readonly=False,
        store=False,
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
    def _compute_product_ref_id(self):
        for move in self:
            move.product_ref_id = move.product_id

    def _inverse_product_ref_id(self):
        for move in self:
            if move.product_ref_id and move.product_id != move.product_ref_id:
                move.product_id = move.product_ref_id

    @api.onchange('product_ref_id')
    def _onchange_product_ref_id(self):
        for move in self:
            if move.product_ref_id and move.product_id != move.product_ref_id:
                move.product_id = move.product_ref_id

    @api.depends('product_id', 'picking_type_id', 'description_picking_manual')
    def _compute_description_picking(self):
        # Description me product ka naam aaye, sirf code nahi
        return super(StockMove, self.with_context(internal_ref_search=False))._compute_description_picking()

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _compute_unit_quantity(self):
        for line in self:
            line.unit_quantity = 0.0
            product = line.product_id
            if not product:
                continue
            try:
                qty = line.product_uom_qty or 0.0
                uom = line.product_uom
                factor = uom.factor or 0.0 if uom else 0.0
                if factor:
                    line.unit_quantity = qty * factor
                else:
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