from odoo import fields, models


class PropertyType(models.Model):
    _name = "property.type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Property Type"

    name = fields.Char(string="Name")