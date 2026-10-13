from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_default_code = fields.Char(
        string='Internal Reference',
        compute='_compute_product_default_code',
        inverse='_inverse_product_default_code',
        store=True,
        readonly=False,
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

    @api.depends('product_id')
    def _compute_product_default_code(self):
        for line in self:
            line.product_default_code = line.product_id.default_code or ''

    def _inverse_product_default_code(self):
        for line in self:
            if line.product_default_code:
                product = self.env['product.product'].search([
                    ('default_code', '=', line.product_default_code)
                ], limit=1)
                if product:
                    line.product_id = product
            else:
                line.product_id = False

    @api.onchange('product_default_code')
    def _onchange_product_default_code(self):
        for line in self:
            if line.product_default_code:
                product = self.env['product.product'].search([
                    ('default_code', '=', line.product_default_code)
                ], limit=1)
                if product:
                    line.product_id = product

    @api.depends('product_id', 'product_qty', 'product_uom_id')
    def _compute_unit_quantity(self):
        for line in self:
            line.unit_quantity = 0.0
            product = line.product_id
            if not product:
                continue
            try:
                qty = line.product_qty or 0.0
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

    def _get_supplierinfo(self):
        self.ensure_one()
        if not self.product_id or not self.order_id.partner_id:
            return self.env['product.supplierinfo']
        partner_id = self.order_id.partner_id.id
        tmpl_id = self.product_id.product_tmpl_id.id
        info = self.env['product.supplierinfo'].search([
            ('extra_partner_ids', 'in', [partner_id]),
            ('extra_product_tmpl_ids', 'in', [tmpl_id]),
        ], limit=1)
        if not info:
            info = self.env['product.supplierinfo'].search([
                ('partner_id', '=', partner_id),
                ('product_tmpl_id', '=', tmpl_id),
            ], limit=1)
        return info

    @api.onchange('product_id', 'order_id')
    def _onchange_product_vendor_apply_supplier_discount(self):
        for line in self:
            if not line.product_id or not line.order_id.partner_id:
                continue
            supplierinfo = line._get_supplierinfo()
            if not supplierinfo:
                continue
            if supplierinfo.min_qty:
                line.product_qty = supplierinfo.min_qty
            if supplierinfo.price:
                line.price_unit = supplierinfo.price
            if supplierinfo.discount_amount:
                line.fixed_amount = supplierinfo.discount_amount
                line.discount_mode = 'amount'
                if line.price_unit:
                    line.discount = min(
                        (supplierinfo.discount_amount / line.price_unit) * 100.0,
                        100.0
                    )
            elif supplierinfo.discount:
                line.discount = supplierinfo.discount
                line.discount_mode = 'percent'
                if line.price_unit:
                    line.fixed_amount = (line.price_unit or 0.0) * (supplierinfo.discount or 0.0) / 100.0

    @api.depends('product_id', 'product_qty', 'product_uom_id', 'partner_id',
                 'order_id.partner_id', 'order_id.currency_id', 'company_id',
                 'date_order', 'order_id.date_order')
    def _compute_price_unit_and_date_planned_and_name(self):
        extra_lines = self.filtered(
            lambda l: l.product_id and l.order_id.partner_id
        )
        for line in extra_lines:
            supplierinfo = line._get_supplierinfo()
            if supplierinfo:
                if supplierinfo.price:
                    line.price_unit = supplierinfo.price
        # Description me product ka naam aaye, sirf code nahi
        super(PurchaseOrderLine, self.with_context(
            internal_ref_search=False
        ))._compute_price_unit_and_date_planned_and_name()

    @api.onchange('discount')
    def _onchange_discount_set_fixed(self):
        for line in self:
            if line.discount_mode == 'amount':
                continue
            line.discount_mode = 'percent' if line.discount else False
            line.fixed_amount = (line.price_unit or 0.0) * (line.discount or 0.0) / 100.0

    @api.onchange('fixed_amount')
    def _onchange_fixed_amount_set_discount(self):
        for line in self:
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
                line.discount = min((line.fixed_amount or 0.0) / price * 100.0, 100.0) if price else 0.0
            else:
                line.fixed_amount = price * (line.discount or 0.0) / 100.0