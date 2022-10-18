from odoo import fields, models, api, _
from datetime import datetime, timedelta
from calendar import monthrange


class TermsAndCondition(models.Model):
    _name = "terms.conditions"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Terms And Condition"
    _order = "sequence, id"

    name = fields.Char(string='Payment Terms', translate=True, required=True)
    sequence = fields.Integer(required=True, default=10)
    value = fields.Selection([
        ('percent', 'Percent'),
        ('fixed', 'Fixed Amount')
    ], string='Type', required=True, default='percent',
        help="Select here the kind of valuation related to this payment terms line.")
    value_amount = fields.Float(string='Value', digits='Payment Terms', help="For percent enter a ratio between 0-100.")
    days = fields.Integer(string='Number of Days', required=True, default=0)
    day_of_the_month = fields.Integer(string='Day of the month')


