from odoo import fields, models, api, _


class PropertyDetails(models.Model):
    _name = "property.details"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Property Details"

    name = fields.Char("Name", required=True)
    street = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    pre_date = fields.Datetime(string="Date", default=fields.Datetime.now, readonly=True)
    no_of_floors = fields.Float("Floor Number")
    name_of_area = fields.Char("Name of Area")
    furnishing = fields.Selection([
        ("not_furnished", "Not Furnished"),
        ("semi_furnished", "Semi Furnished"),
        ("Fully_furnished", "Fully Furnished"),
        ],
        string="Furnishing", default="not_furnished")
    property_type = fields.Many2one("property.type", required=True, string="Property Type")
    property_manager = fields.Many2one("res.users", required=True, string="Property Manager")
    facing = fields.Char("Facing")
    rooms = fields.Float("Rooms")
    bathrooms = fields.Float("Bathrooms")
    carpet_area = fields.Float("Carpter Area(Sqft)")
    video_url = fields.Char("Video URL")
    code = fields.Char(
        "Code", readonly=True, index=True, default=lambda self: _('New'))
    currency = fields.Many2one("res.currency", "Currency")
    property_value = fields.Float("Rental Price")
    image = fields.Binary("Image")
    add_image = fields.One2many("image.details", "details", string='Property Image')
    child_ids = fields.One2many('res.partner', 'parent_id', string='Contact', domain=[('active', '=', True)])
    state = fields.Selection([
        ("available", "Available"),
        ("on_lease", "On Lease"),
        ("booked", "Booked"),
        ("sold", "sold"),
        ],
        string="State", default="available")
    color = fields.Integer()

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('property.detail') or _('New')

        result = super(PropertyDetails, self).create(vals)
        return result

    def state_available(self):
        self.update({"state": "available"})

    def state_booked(self):
        self.update({"state": "booked"})

    def state_onlease(self):
        self.update({"state": "on_lease"})

    def state_sold(self):
        self.update({"state": "sold"})


class ImageDetails(models.Model):
    _name = "image.details"
    _description = "Image Details"

    photo = fields.Binary("Image")
    details = fields.Many2one("property.details", index=True)