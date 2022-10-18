from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare

from werkzeug.urls import url_encode


class PropertySale(models.Model):
    _name = "property.sale"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Property Sales"

    name = fields.Char(
        "Code", readonly=True, index=True, default=lambda self: _('New'))
    property = fields.Many2one("property.details", required=True, string="Property")
    property_owner = fields.Many2one("res.partner", required=True, string="Property Owner")
    property_cost = fields.Float(string="Property Cost", compute="_amount_all", tracking=5)
    property_buyer = fields.Many2one("res.partner", required=True, string="Property Buyer")
    date = fields.Datetime(string="Date", required=True)
    deal_amount = fields.Float(string="Deal Amount")
    state = fields.Selection([
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("sold", "Sold"),
        ],
        string="State", default="new")
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced', readonly=True)
    invoice_ids = fields.Many2many("account.move", string='Invoices', compute="_get_invoiced", readonly=True,
                                   copy=False, search="_search_invoice_ids")
    tax_id = fields.Many2one('account.tax', string='Taxe',
                             domain=['|', ('active', '=', False), ('active', '=', True)])
    invoice_lines = fields.Many2many('account.move.line', 'property_invoice_rel', 'property_id', 'invoice_line_id', string='Invoice Line', copy=False)
    count_invoice_amount = fields.Float('Invoice Amount', compute='_count_invoice_amount')
    sec_state = fields.Selection([
        ("invoiced", "Invoiced"),
        ("not_invoiced", "Not Invoiced"),
        ],
        string="State", default="not_invoiced")

    def _count_invoice_amount(self):
        for property in self:
            account_move_line_ids = self.env['account.move.line'].search([('name', '=', property.name)])
            customer_count = 0.0
            vendor_count = 0.0
            for line in account_move_line_ids:
                if line.move_id.type == "out_invoice" or line.move_id.type == "in_refund":
                    customer_count += line.price_subtotal
                else:
                    vendor_count += line.price_subtotal
            property.count_invoice_amount = customer_count
            property.count_incoming_invoice_amount = vendor_count

    def invoice_amount_button(self):
        self.ensure_one()
        return {
            'name': 'Invoice Amount',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'domain': [('name', '=', self.name), ('move_id.type', 'in', ['out_invoice', 'in_refund'])],
        }

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('property.sale') or _('New')

        result = super(PropertySale, self).create(vals)
        return result

    @api.depends('property.property_value')
    def _amount_all(self):
        for order in self:
            order.update({
                'property_cost': order.property.property_value,
            })

    @api.depends('property.state')
    def details_update_sold(self):
        for order in self:
            order.property.update({"state": "sold"})

    def state_inprogress(self):
        self.update({"state": "in_progress"})

    def state_sold(self):
        self.update({"state": "sold"})
        self.details_update_sold()

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.property_owner.id,
                'default_invoice_origin': self.mapped('name'),
            })
        action['context'] = context
        return action

