import uuid

from odoo import models, fields, api

# Ye fields group ke sab records me barabar rehte hain
GROUP_FIELDS = [
    'price', 'min_qty', 'date_start', 'date_end', 'delay',
    'discount', 'discount_amount', 'discount_mode', 'currency_id',
]


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    extra_partner_ids = fields.Many2many(
        'res.partner',
        'supplierinfo_extra_partner_rel',
        'supplierinfo_id',
        'partner_id',
        string='Vendors',
    )
    extra_product_tmpl_ids = fields.Many2many(
        'product.template',
        'supplierinfo_extra_tmpl_rel',
        'supplierinfo_id',
        'product_tmpl_id',
        string='Products',
    )
    multi_group = fields.Char(string='Multi Group', index=True, copy=False)
    discount_amount = fields.Float(
        string='Discount Amount',
        digits='Product Price',
        default=0.0,
    )
    discount_mode = fields.Selection(
        [('percent', 'Percent'), ('amount', 'Amount')],
        string='Discount Mode',
        copy=True,
    )

    @api.onchange('extra_partner_ids')
    def _onchange_extra_partner_ids(self):
        for rec in self:
            if not rec.extra_partner_ids:
                rec.partner_id = False
            elif rec.partner_id not in rec.extra_partner_ids:
                rec.partner_id = rec.extra_partner_ids[:1]

    @api.onchange('extra_product_tmpl_ids')
    def _onchange_extra_product_tmpl_ids(self):
        for rec in self:
            if not rec.extra_product_tmpl_ids:
                rec.product_tmpl_id = False
            elif rec.product_tmpl_id not in rec.extra_product_tmpl_ids:
                rec.product_tmpl_id = rec.extra_product_tmpl_ids[:1]

    @api.onchange('discount')
    def _onchange_discount_set_amount(self):
        for rec in self:
            if rec.discount_mode == 'amount':
                continue
            rec.discount_mode = 'percent' if rec.discount else False
            rec.discount_amount = (rec.price or 0.0) * (rec.discount or 0.0) / 100.0

    @api.onchange('discount_amount')
    def _onchange_amount_set_discount(self):
        for rec in self:
            if rec.discount_mode == 'percent':
                continue
            if rec.discount_amount:
                rec.discount_mode = 'amount'
                price = rec.price or 0.0
                rec.discount = min(rec.discount_amount / price * 100.0, 100.0) if price else 0.0
            else:
                rec.discount_mode = False
                rec.discount = 0.0

    @api.onchange('price')
    def _onchange_price_sync_discount(self):
        for rec in self:
            price = rec.price or 0.0
            if rec.discount_mode == 'amount':
                rec.discount = min((rec.discount_amount or 0.0) / price * 100.0, 100.0) if price else 0.0
            else:
                rec.discount_amount = price * (rec.discount or 0.0) / 100.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('skip_combo'):
            return records
        for rec in records:
            if not rec.extra_partner_ids and not rec.extra_product_tmpl_ids:
                rec.with_context(skip_combo=True).write({
                    'extra_partner_ids': [(6, 0, rec.partner_id.ids)],
                    'extra_product_tmpl_ids': [(6, 0, rec.product_tmpl_id.ids)],
                })
                continue
            rec._sync_group()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_combo'):
            return res
        tags_changed = 'extra_partner_ids' in vals or 'extra_product_tmpl_ids' in vals
        common_changed = any(k in vals for k in GROUP_FIELDS)
        for rec in self:
            if not rec.exists():
                continue
            if tags_changed or common_changed:
                rec._sync_group()
        return res

    def _group_records(self):
        self.ensure_one()
        if not self.multi_group:
            return self
        return self.with_context(skip_combo=True, active_test=False).search(
            [('multi_group', '=', self.multi_group)]
        )

    def _sync_group(self):
        for rec in self:
            if not rec.exists():
                continue
            if not rec.multi_group:
                rec.with_context(skip_combo=True).write({'multi_group': uuid.uuid4().hex})
            token = rec.multi_group
            rec = rec.with_context(skip_combo=True)
            Model = self.with_context(skip_combo=True, active_test=False)

            partners = rec.extra_partner_ids | rec.partner_id
            templates = rec.extra_product_tmpl_ids | rec.product_tmpl_id
            group = rec._group_records()

            # ---- Sirf ek record rakho (primary), baaki delete karo ----
            if len(group) > 1:
                primary = rec
                others = group - primary
                if others:
                    others.unlink()
                group = primary

            # Primary record par hi saare tags set karo
            group.write({
                'extra_partner_ids': [(6, 0, partners.ids)],
                'extra_product_tmpl_ids': [(6, 0, templates.ids)],
            })

            # Primary partner_id / product_tmpl_id ko pehla vendor/product rakho
            vals = {}
            if partners and group.partner_id not in partners:
                vals['partner_id'] = partners[:1].id
            if templates and group.product_tmpl_id not in templates:
                vals['product_tmpl_id'] = templates[:1].id
                vals['product_id'] = False
                vals['product_uom_id'] = templates[:1].uom_id.id
            if vals:
                group.with_context(skip_combo=True).write(vals)

    @api.model
    def _init_multi_tags(self):
        for rec in self.with_context(skip_combo=True, active_test=False).search([]):
            vals = {}
            if rec.partner_id and rec.partner_id not in rec.extra_partner_ids:
                vals['extra_partner_ids'] = [(4, rec.partner_id.id)]
            if rec.product_tmpl_id and rec.product_tmpl_id not in rec.extra_product_tmpl_ids:
                vals['extra_product_tmpl_ids'] = [(4, rec.product_tmpl_id.id)]
            if vals:
                rec.write(vals)