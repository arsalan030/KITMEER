from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Sale Order confirm hone ke baad Delivery moves ki price_unit set karo."""
        result = super().action_confirm()
        for order in self:
            for line in order.order_line:
                if not line.product_id:
                    continue

                # Pehle try karo sale_line_id se match karna
                moves = self.env['stock.move'].search([
                    ('sale_line_id', '=', line.id),
                    ('state', 'not in', ('done', 'cancel')),
                ])

                # Agar sale_line_id se na mile, to origin + product se match karo
                if not moves:
                    moves = self.env['stock.move'].search([
                        ('origin', '=', order.name),
                        ('product_id', '=', line.product_id.id),
                        ('state', 'not in', ('done', 'cancel')),
                    ])

                # Ab moves ki price_unit update karo
                for move in moves:
                    move.price_unit = line.price_unit

        return result