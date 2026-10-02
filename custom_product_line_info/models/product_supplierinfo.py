import uuid

from odoo import models, fields, api

# Ye fields group ke sab records me barabar rehte hain
GROUP_FIELDS = [
    'price', 'min_qty', 'date_start', 'date_end', 'delay',
    'discount', 'discount_amount', 'discount_mode', 'currency_id',
]


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    # Form me ye tags wale fields dikhte hain: chune hue SAB vendors/products.
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

    # ------------------------------------------------------------------
    # Vendors / Products tags
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Discount (%) <-> Discount Amount: ek bharo, doosri auto fill + readonly
    # ------------------------------------------------------------------
    @api.onchange('discount')
    def _onchange_discount_set_amount(self):
        for rec in self:
            # Amount se convert hua discount ho to mode na badlein
            if rec.discount_mode == 'amount':
                continue
            rec.discount_mode = 'percent' if rec.discount else False
            rec.discount_amount = (rec.price or 0.0) * (rec.discount or 0.0) / 100.0

    @api.onchange('discount_amount')
    def _onchange_amount_set_discount(self):
        for rec in self:
            # Percent mode me amount readonly hai
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
                # Amount wahi rahe, percent dobara calculate ho
                rec.discount = min((rec.discount_amount or 0.0) / price * 100.0, 100.0) if price else 0.0
            else:
                rec.discount_amount = price * (rec.discount or 0.0) / 100.0

    # ------------------------------------------------------------------
    # Group: har vendor x product ka alag asli record, values/tags sab me same
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('skip_combo'):
            return records
        for rec in records:
            # Core code (jaise PO confirm) se bane records me tags khali hote hain
            if not rec.extra_partner_ids and not rec.extra_product_tmpl_ids:
                rec.with_context(skip_combo=True).write({
                    'extra_partner_ids': [(6, 0, rec.partner_id.ids)],
                    'extra_product_tmpl_ids': [(6, 0, rec.product_tmpl_id.ids)],
                })
                continue
            partners = rec.extra_partner_ids | rec.partner_id
            templates = rec.extra_product_tmpl_ids | rec.product_tmpl_id
            if len(partners) > 1 or len(templates) > 1:
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
            if tags_changed or (common_changed and rec.multi_group):
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
        """Tags ke mutabiq group ke records banao/hatao, aur sab me
        price/validity/discount/discount amount barabar karo."""
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

            # Same combination ke duplicate records hata do (is record ko rakho)
            seen = {(rec.partner_id.id, rec.product_tmpl_id.id)}
            duplicates = Model.browse()
            for other in group - rec:
                key = (other.partner_id.id, other.product_tmpl_id.id)
                if key in seen:
                    duplicates |= other
                else:
                    seen.add(key)
            if duplicates:
                duplicates.unlink()
                group -= duplicates

            # Jo combination ab tags me nahi, unke records delete
            wanted = {(p.id, t.id) for p in partners for t in templates}
            stale = (group - rec).filtered(
                lambda r: (r.partner_id.id, r.product_tmpl_id.id) not in wanted
            )
            if stale:
                stale.unlink()
                group -= stale

            # Nayi combinations: pehle se maujood record ko shamil karo, warna naya banao
            existing = {(r.partner_id.id, r.product_tmpl_id.id) for r in group}
            for partner in partners:
                for tmpl in templates:
                    if (partner.id, tmpl.id) in existing:
                        continue
                    base = [
                        ('partner_id', '=', partner.id),
                        ('product_tmpl_id', '=', tmpl.id),
                        ('min_qty', '=', rec.min_qty),
                    ]
                    match = Model.search(base + [('multi_group', '=', False)], limit=1)
                    if match:
                        match.write({'multi_group': token})
                        group |= match
                        continue
                    # Kisi doosre group me ye combination ho to dobara na banao
                    if Model.search_count(base + [('multi_group', '!=', False)]):
                        continue
                    defaults = {
                        'partner_id': partner.id,
                        'product_tmpl_id': tmpl.id,
                        'multi_group': token,
                    }
                    if tmpl != rec.product_tmpl_id:
                        defaults['product_id'] = False
                        defaults['product_uom_id'] = tmpl.uom_id.id
                    group |= rec.copy(defaults)

            group = group.with_context(skip_combo=True)

            # Sab records me tags barabar
            group.write({
                'extra_partner_ids': [(6, 0, partners.ids)],
                'extra_product_tmpl_ids': [(6, 0, templates.ids)],
            })

            # Sab records me price, validity, discount, discount amount barabar
            others = group - rec
            if others:
                others.write({
                    'price': rec.price,
                    'min_qty': rec.min_qty,
                    'date_start': rec.date_start,
                    'date_end': rec.date_end,
                    'delay': rec.delay,
                    'discount': rec.discount,
                    'discount_amount': rec.discount_amount,
                    'discount_mode': rec.discount_mode,
                    'currency_id': rec.currency_id.id,
                })

    @api.model
    def _init_multi_tags(self):
        """Purane records me tags wale fields me unka apna vendor/product bharo."""
        for rec in self.with_context(skip_combo=True, active_test=False).search([]):
            vals = {}
            if rec.partner_id and rec.partner_id not in rec.extra_partner_ids:
                vals['extra_partner_ids'] = [(4, rec.partner_id.id)]
            if rec.product_tmpl_id and rec.product_tmpl_id not in rec.extra_product_tmpl_ids:
                vals['extra_product_tmpl_ids'] = [(4, rec.product_tmpl_id.id)]
            if vals:
                rec.write(vals)