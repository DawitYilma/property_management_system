
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    tenant_line_ids = fields.Char(string='Property Sale', readonly=True, copy=False)





