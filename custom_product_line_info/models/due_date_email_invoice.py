import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    overdue_email_sent = fields.Boolean(
        string='Overdue Email Sent',
        default=False,
        copy=False,
    )

    @api.model
    def _cron_send_overdue_invoice_emails(self):
        """Daily cron: overdue invoices ke customers ko email bhejo."""
        _logger.info("=" * 60)
        _logger.info("OVERDUE INVOICE EMAIL CRON: STARTED")

        today = fields.Date.context_today(self)
        _logger.info("OVERDUE CRON: Today = %s", today)

        invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('invoice_date_due', '<', today),
            ('overdue_email_sent', '=', False),
        ])

        _logger.info("OVERDUE CRON: %s overdue invoices mile", len(invoices))

        if not invoices:
            _logger.info("OVERDUE CRON: Koi overdue invoice nahi mili. Exit.")
            _logger.info("=" * 60)
            return

        template = self.env.ref(
            'custom_product_line_info.email_template_overdue_invoice',
            raise_if_not_found=False,
        )
        if not template:
            _logger.error("OVERDUE CRON: Email template nahi mila! "
                          "(custom_product_line_info.email_template_overdue_invoice)")
            _logger.info("=" * 60)
            return

        _logger.info("OVERDUE CRON: Template mila = %s", template.name)

        sent_count = 0
        skip_count = 0
        fail_count = 0

        for invoice in invoices:
            _logger.info("-" * 50)
            _logger.info("OVERDUE CRON: Processing Invoice = %s | Customer = %s",
                         invoice.name, invoice.partner_id.name)

            if not invoice.partner_id.email:
                _logger.warning("OVERDUE CRON: SKIP -> Customer ka email nahi hai. "
                                "Invoice = %s | Customer = %s",
                                invoice.name, invoice.partner_id.name)
                skip_count += 1
                continue

            _logger.info("OVERDUE CRON: Sending email to = %s",
                         invoice.partner_id.email)

            try:
                template.send_mail(invoice.id, force_send=True)
                invoice.overdue_email_sent = True
                sent_count += 1
                _logger.info("OVERDUE CRON: SUCCESS -> Email sent for Invoice = %s",
                             invoice.name)
            except Exception as e:
                fail_count += 1
                _logger.exception("OVERDUE CRON: FAILED -> Invoice = %s | Error = %s",
                                  invoice.name, str(e))
                continue

        _logger.info("=" * 60)
        _logger.info("OVERDUE CRON: SUMMARY -> Sent = %s | Skipped = %s | Failed = %s",
                     sent_count, skip_count, fail_count)
        _logger.info("OVERDUE INVOICE EMAIL CRON: FINISHED")
        _logger.info("=" * 60)