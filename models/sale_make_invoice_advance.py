
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    advance_payment_method = fields.Selection(
        [
            ("delivered", "Regular invoice"),
            ("percentage", "Down payment (percentage)"),
            ("fixed", "Down payment (fixed amount)"),
        ],
        string="Create Invoice",
        default="delivered",
        required=True,
        help="""A standard invoice is issued with all the order lines ready for
        invoicing, according to their invoicing policy
        (based on ordered or delivered quantity).""",
    )

    def create_invoices(self):
        if self._context.get("active_model") == "payment.information":
            for order in self:
                ctx = self.env.context.copy()
                if self._context.get("active_model") == "payment.information":
                    PaymentInformation = order.env["payment.information"]
                    ProductLine = self.env['product.line']
                    proline = ProductLine.browse(self._context.get("active_ids", []))
                    print(proline.product_id)
                    payment = PaymentInformation.browse(order._context.get("active_ids", []))
                    print(len(payment.product_line))
                    rec = PaymentInformation.search([('date', '=', payment.date), ('name', '=', payment.name)])
                    if rec:
                        rec.state = 'paid'
                val = []
                for pro in payment.product_line:
                    val.append(
                        (0, 0, {'payment_information_ids': payment.name, 'quantity': 1, 'price_unit': pro.price_unit,
                                'name': payment.line_id, 'product_id': pro.product_id}))
                invoice = self.env['account.move'].create({
                    'state': 'draft',
                    'type': 'out_invoice',
                    'partner_id': payment.partner_id.id,
                    'invoice_line_ids': val
                })
                invoice.post()
                action = {
                    'type': 'ir.actions.act_window',
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'views': [(self.env.ref('account.view_move_form').id, 'form')],
                }

            return action
        elif self._context.get("active_model") == "tenant.details.line":
            for order in self:
                ctx = self.env.context.copy()
                if self._context.get("active_model") == "tenant.details.line":
                    TenantDetails = self.env["tenant.details.line"]
                    rent = TenantDetails.browse(self._context.get("active_ids", []))
                    rec = TenantDetails.search([('date', '=', rent.date), ('name', '=', rent.name)])
                    if rec:
                        rec.state = 'paid'

                invoice = self.env['account.move'].create({
                    'state': 'draft',
                    'type': 'out_invoice',
                    'partner_id': rent.tenant.id,
                    'invoice_line_ids': [(0, 0, {'tax_ids': rent.tax_id, 'tenant_line_ids': rent.name, 'quantity': 1,
                                                 'price_unit': rent.tent_amount, 'name': rent.line_id}),
                                         (0, 0, {'tax_ids': rent.tax_id, 'tenant_line_ids': rent.name, 'quantity': 1,
                                                 'price_unit': rent.utility_price, 'name': rent.utility_id})]
                })
                invoice.post()
                action = {
                    'type': 'ir.actions.act_window',
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'views': [(self.env.ref('account.view_move_form').id, 'form')],
                }
            return action

        elif self._context.get("active_model") == "property.sale":
            for order in self:
                ctx = self.env.context.copy()
                PropertySale = self.env["property.sale"]
                sold = PropertySale.browse(self._context.get("active_ids", []))
                rec = PropertySale.search([('name', '=', sold.name)])
                if rec:
                    rec.sec_state = 'invoiced'
                if self._context.get("active_model") == "property.sale":
                    PropertySale = self.env["property.sale"]
                    sale = PropertySale.browse(self._context.get("active_ids", []))

                invoice = self.env['account.move'].create({
                    'state': 'draft',
                    'type': 'out_invoice',
                    'partner_id': sale.property_buyer.id,
                    'invoice_line_ids': [(0, 0, {'tax_ids': sale.tax_id, 'quantity': 1, 'price_unit': sale.deal_amount,
                                                 'name': sale.name})]
                })
                invoice.post()
                action = {
                    'type': 'ir.actions.act_window',
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'views': [(self.env.ref('account.view_move_form').id, 'form')],
                }

            return action

        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            sale_orders._create_invoices(final=self.deduct_down_payments)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id',
                                                                 self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                amount, name = self._get_advance_details(order)

                if self.product_id.invoice_policy != 'order':
                    raise UserError(
                        _('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(
                        _("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id,
                                                               order.partner_shipping_id).ids
                else:
                    tax_ids = taxes.ids
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]

                so_line_values = self._prepare_so_line(order, analytic_tag_ids, tax_ids, amount)
                so_line = sale_line_obj.create(so_line_values)
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}
