from odoo import fields, models, api, _


class PropertyMaintenance(models.Model):
    _name = "property.maintenance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Property Maintenance"

    customer_group = fields.Boolean(compute="set_access_for_product")
    name = fields.Char("Name", required=True)
    pre_date = fields.Datetime(string="Date", default=fields.Datetime.now, readonly=True)
    main_date = fields.Datetime(string="End date of Maintenance")
    floors = fields.Char("Floor")
    property = fields.Many2one("property.details", string="Property")
    customer_property = fields.Char(string="Customer Given Property Name")
    property_manager = fields.Many2one("res.users", string="Property Manager")
    created_by = fields.Many2one("res.users", string="Created By", default=lambda self: self.env.user, readonly=True)
    code = fields.Char(
        "Code", readonly=True, index=True, default=lambda self: _('New'))
    maintenance_value = fields.Float("Maintenance Value")
    maintenance_type = fields.Many2one("maintenance.type", string="Maintenance Type")
    child_ids = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ("new", "New"),
        ("in_process", "In Process"),
        ("done", "Done"),
    ],
        string="State", default="new")
    product_in_maintenance = fields.Text()
    color = fields.Integer()

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('property.maintenance') or _('New')

        result = super(PropertyMaintenance, self).create(vals)
        return result

    def details_update_inprocess(self):
        self.update({"state": "in_process"})

    def details_update_done(self):
        self.update({"state": "done"})

    def set_access_for_product(self):
        self.customer_group = self.env['res.users'].has_group('property_management_system.group_view_customer')


class MaintenanceType(models.Model):
    _name = "maintenance.type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Maintenance Type"

    name = fields.Char(string="Name")