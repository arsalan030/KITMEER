from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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
                if product.packaging_ids:
                    line.unit_quantity = product.packaging_ids[0].qty
                elif product.product_tmpl_id.packaging_ids:
                    line.unit_quantity = product.product_tmpl_id.packaging_ids[0].qty
            except Exception:
                line.unit_quantity = 0.0

    def _get_supplierinfo(self):
        """Helper: extra_* fields se supplierinfo dhoondo, fallback standard."""
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
        """Product aur Vendor select hone par Pricelist se price, quantity aur discount apply karo."""
        for line in self:
            if not line.product_id or not line.order_id.partner_id:
                continue
            supplierinfo = line._get_supplierinfo()
            if not supplierinfo:
                continue

            # Quantity
            if supplierinfo.min_qty:
                line.product_qty = supplierinfo.min_qty
            # Price
            if supplierinfo.price:
                line.price_unit = supplierinfo.price
            # Discount
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
        """Odoo 19 standard compute ko override karo taake extra_* fields se price aaye."""
        extra_lines = self.filtered(
            lambda l: l.product_id and l.order_id.partner_id
        )
        for line in extra_lines:
            supplierinfo = line._get_supplierinfo()
            if supplierinfo:
                if supplierinfo.price:
                    line.price_unit = supplierinfo.price

        super()._compute_price_unit_and_date_planned_and_name()

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