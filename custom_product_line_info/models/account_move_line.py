from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_default_code = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        readonly=True
    )
    product_ref_id = fields.Many2one(
        'product.product',
        string='Internal Reference',
        compute='_compute_product_ref_id',
        inverse='_inverse_product_ref_id',
        readonly=False,
        store=False,
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
    def _compute_product_ref_id(self):
        for line in self:
            line.product_ref_id = line.product_id

    def _inverse_product_ref_id(self):
        for line in self:
            if line.product_ref_id and line.product_id != line.product_ref_id:
                line.product_id = line.product_ref_id

    @api.onchange('product_ref_id')
    def _onchange_product_ref_id(self):
        for line in self:
            if line.product_ref_id and line.product_id != line.product_ref_id:
                line.product_id = line.product_ref_id

    @api.depends('product_id', 'move_id.ref', 'move_id.payment_reference')
    def _compute_name(self):
        # Description me product ka naam aaye, sirf code nahi
        return super(AccountMoveLine, self.with_context(internal_ref_search=False))._compute_name()

    @api.depends('product_id', 'quantity', 'product_uom_id')
    def _compute_unit_quantity(self):
        for line in self:
            line.unit_quantity = 0.0
            product = line.product_id
            if not product:
                continue
            try:
                qty = line.quantity or 0.0
                uom = line.product_uom_id
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