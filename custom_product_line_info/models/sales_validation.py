from odoo import models, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('partner_id', 'amount_total', 'state')
    def _check_credit_limit(self):
        for order in self:
            # Sirf confirmed orders par check karein
            if order.state not in ['sale', 'done']:
                continue
            if not order.partner_id:
                continue
            # Credit limit set hai ya nahi
            partner = order.partner_id
            if partner.credit_limit <= 0:
                continue
            # Customer ka current outstanding + is order ka amount
            # Credit limit exceed ho rahi hai?
            total_receivable = partner.credit + order.amount_total
            if total_receivable > partner.credit_limit:
                raise ValidationError(_(
                    "Customer credit limit exceeded!\n"
                    "Credit Limit: %s\n"
                    "Current Receivable: %s\n"
                    "This Order Amount: %s\n"
                    "Total After This Order: %s"
                ) % (
                    partner.credit_limit,
                    partner.credit,
                    order.amount_total,
                    total_receivable
                ))