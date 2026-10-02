from odoo import models, fields, api


class MultiSupplierInfo(models.Model):
    _name = 'multi.supplierinfo'
    _description = 'Multi Vendor Product Pricelist'

    name = fields.Char(string='Reference', default='New')
    partner_ids = fields.Many2many(
        'res.partner',
        'multi_supplierinfo_partner_rel',
        'multi_supplierinfo_id',
        'partner_id',
        string='Vendors',
        required=True,
    )
    product_tmpl_ids = fields.Many2many(
        'product.template',
        'multi_supplierinfo_product_tmpl_rel',
        'multi_supplierinfo_id',
        'product_tmpl_id',
        string='Products',
        required=True,
    )
    price = fields.Float(string='Unit Price', digits='Product Price', default=0.0)
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    discount_amount = fields.Float(string='Discount Amount', digits='Product Price', default=0.0)
    min_qty = fields.Float(string='Min Quantity', default=0.0)
    date_start = fields.Date(string='Validity Start')
    date_end = fields.Date(string='Validity End')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.onchange('discount')
    def _onchange_discount_set_amount(self):
        for rec in self:
            if rec.discount:
                rec.discount_amount = (rec.price or 0.0) * (rec.discount or 0.0) / 100.0
            else:
                rec.discount_amount = 0.0

    @api.onchange('discount_amount')
    def _onchange_amount_set_discount(self):
        for rec in self:
            if rec.discount_amount and rec.price:
                rec.discount = min((rec.discount_amount / rec.price) * 100.0, 100.0)
            elif not rec.discount_amount:
                rec.discount = 0.0

    @api.onchange('price')
    def _onchange_price_sync_discount(self):
        for rec in self:
            if rec.discount:
                rec.discount_amount = (rec.price or 0.0) * (rec.discount or 0.0) / 100.0