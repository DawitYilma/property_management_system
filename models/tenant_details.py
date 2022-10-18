from odoo import fields, models, api, _
from datetime import datetime, timedelta, date
from calendar import monthrange


class TenantDetails(models.Model):
    _name = "tenant.details"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Tenant Detail"

    code = fields.Char(
        "Code", readonly=True, index=True, default=lambda self: _('New'))
    name = fields.Char("Name", required=True)
    property = fields.Many2one("property.details", required=True, string="Property")
    tenant = fields.Many2one("res.partner", required=True, string="Tenant")
    start_date = fields.Datetime(string="Start Date", required=True)
    end_date = fields.Datetime(string="End Date", required=True)
    date = fields.Datetime(string="Calculated Date")
    rent_type = fields.Selection([
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("semi_annual", "Semi-Annual"),
            ("annual", "Annual"),
        ],
        string="Rent Type",
        default="monthly", required=True,
        )
    state = fields.Selection([
        ("available", "Available"),
        ("on_lease", "On Lease"),
        ("booked", "Booked"),
        ("closed", "Closed"),
        ("sold", "sold"),
        ],
        string="State", default="available")
    tenant_rent = fields.Float("Tenant Rent", store=True, readonly=False, compute="_amount_add")
    currency = fields.Many2one("res.currency", "Currency")
    deposit = fields.Float("Deposit")
    deposit_received = fields.Boolean('Deposit Received')
    total_rent = fields.Float("Total Rent", compute="_compute_total_amount")
    deposit_return = fields.Float("Deposit Return")
    deposit_returned = fields.Boolean("Deposit Returned")
    image = fields.Binary(string="Image")
    tenant_property_line = fields.One2many('tenant.details.line', 'tenant_details', string='Rent Details',
                                 states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True,
                                 auto_join=True)
    count_invoice_amount = fields.Float('Invoice Amount', compute='_count_invoice_amount')
    utility = fields.Selection([
        ("without_utility", "WithOut Utility"),
        ("with_utility", "With Utility"),
        ],
        string="Utility", default="without_utility")
    totalleft = fields.Float("Total Left")
    dff_date = fields.Float("Dff Date")
    terms = fields.Many2one("terms.conditions", string="Terms And Conditions")

    def compute_dffdate(self):
        for rent in self:
            if(rent.tenant_property_line.tenant_details == self.id & rent.tenant_property_line.state == 'unpaid'):
                prev_days = monthrange(rent.tenant_property_line.date.year, rent.tenant_property_line.date.month)[1]
                rec_days = monthrange(datetime.now().strftime("%Y"), datetime.now().strftime("%m"))[1]
                time = rent.tenant_property_line.date.year * 365 + rent.tenant_property_line.date.month * prev_days + rent.tenant_property_line.date.day
                now_time = int(datetime.now().strftime("%Y")) * 365 + int(datetime.now().strftime("%m")) * 30 + int(datetime.now().strftime("%d"))
                dif = now_time - time
                rent.update({
                    'dff_date': dif,
                })

    @api.depends('property.property_value', 'property.currency')
    def _amount_add(self):
        for order in self:
            order.update({
                'tenant_rent': order.property.property_value,
                'currency': order.property.currency,
            })
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.depends('tenant_property_line.tenant_line_ids')
    def _input_code(self):
        for invoice in self:
            invoice.tenant_property_line.tenant_line_ids.update({"tenant_line_ids": invoice.code})
            tenant_line_ids = self.tenant_id.code

    def _count_invoice_amount(self):
        for property in self:
            account_move_line_ids = self.env['account.move.line'].search([('tenant_line_ids', '=', property.code)])
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
            'domain': [('tenant_line_ids', '=', self.code), ('move_id.type', 'in', ['out_invoice', 'in_refund'])],
        }

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tenant.details') or _('New')

        result = super(TenantDetails, self).create(vals)
        return result

    @api.depends('property.state')
    def details_update_sold(self):
        self.update({"state": "sold"})
        for order in self:
            order.property.update({"state": "sold"})

    @api.depends('property.state')
    def details_update_closed(self):
        self.update({"state": "closed"})
        for order in self:
            order.property.update({"state": "available"})

    @api.depends('property.state')
    def details_update_available(self):
        self.update({"state": "available"})
        for order in self:
            order.property.update({"state": "available"})

    @api.depends('property.state')
    def details_update_booked(self):
        self.update({"state": "booked"})
        for order in self:
            order.property.update({"state": "booked"})

    @api.depends('property.state')
    def details_update_onlease(self):
        self.update({"state": "on_lease"})
        for order in self:
            order.property.update({"state": "on_lease"})

    def _compute_total_amount(self):
        for rent in self:
            amount_per_dayt = rent.tenant_rent / 30
            monthst = int(rent.end_date.month) - int(rent.start_date.month)
            yearst = int(rent.end_date.year) - int(rent.start_date.year)
            totalmonthst = monthst + (yearst * 12)
            if totalmonthst == 0:
                rent.total_rent = rent.tenant_rent
            if totalmonthst >= 1:
                if rent.rent_type == "monthly":
                    amount_per_day = rent.tenant_rent / 30
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=30)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                        prev_date = rent.date
                        rent.date = rent.date + timediff
                        if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                            rent.total_rent += abs(rent.tenant_rent)

                        else:
                            break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (
                                        rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)

                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (
                                        prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)

                if rent.rent_type == "quarterly":
                    amount_per_day = rent.tenant_rent / 90
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=90)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                        prev_date = rent.date
                        rent.date = rent.date + timediff
                        if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                            rent.total_rent += abs(rent.tenant_rent)

                        else:
                            break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (
                                        rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)

                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (
                                        prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)

                if rent.rent_type == "semi_annual":
                    amount_per_day = rent.tenant_rent / 180
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=180)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                        prev_date = rent.date
                        rent.date = rent.date + timediff
                        if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                            rent.total_rent += abs(rent.tenant_rent)

                        else:
                            break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)

                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)

                if rent.rent_type == "annual":
                    amount_per_day = rent.tenant_rent / 365
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=365)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                        prev_date = rent.date
                        rent.date = rent.date + timediff
                        if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                            rent.total_rent += abs(rent.tenant_rent)
                        else:
                            break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)

                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        rent.total_rent += abs(totalleft)
            else:
                if rent.end_date.year > rent.start_date.year or rent.end_date.year == rent.start_date.year and rent.end_date.month - rent.start_date.month > 0 or rent.end_date.year == rent.start_date.year and rent.end_date.month - rent.start_date.month == 0 and rent.end_date.day > rent.start_date.day:
                    rent.total_rent = abs(rent.tenant_rent)
        return True

    def compute_rent(self):
        for rent in self:
            amount_per_dayt = rent.tenant_rent / 30
            monthst = int(rent.end_date.month) - int(rent.start_date.month)
            yearst = int(rent.end_date.year) - int(rent.start_date.year)
            totalmonthst = monthst + (yearst * 12)
            if totalmonthst == 0:
                tenant_rent = self.tenant_property_line.create({
                    'name': rent.code,
                    'date': rent.start_date,
                    'tent_amount': abs(rent.tenant_rent),
                    'comp_amount': abs(rent.tenant_rent),
                    'tenant': rent.tenant.id,
                    'tenant_details': self.id,
                })
            if totalmonthst >= 1:
                if rent.rent_type == "monthly":
                    amount_per_day = rent.tenant_rent / 30
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=30)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                        prev_date = rent.date
                        rent.date = rent.date + timediff
                        if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                            tenant_rent = self.tenant_property_line.create({
                                'name': rent.code,
                                'date': rent.date,
                                'tent_amount': abs(rent.tenant_rent),
                                'comp_amount': abs(rent.tenant_rent),
                                'tenant': rent.tenant.id,
                                'tenant_details': self.id,
                            })
                        else:
                            break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (
                                        rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })
                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (
                                        prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })

                if rent.rent_type == "quarterly":
                    amount_per_day = rent.tenant_rent / 90
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=90)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                            prev_date = rent.date
                            rent.date = rent.date + timediff
                            if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                                tenant_rent = self.tenant_property_line.create({
                                    'name': rent.code,
                                    'date': rent.date,
                                    'tent_amount': abs(rent.tenant_rent),
                                    'comp_amount': abs(rent.tenant_rent),
                                    'tenant': rent.tenant.id,
                                    'tenant_details': self.id,
                                })
                            else:
                                break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })
                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })

                if rent.rent_type == "semi_annual":
                    amount_per_day = rent.tenant_rent / 180
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=180)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                            prev_date = rent.date
                            rent.date = rent.date + timediff
                            if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                                tenant_rent = self.tenant_property_line.create({
                                    'name': rent.code,
                                    'date': rent.date,
                                    'tent_amount': abs(rent.tenant_rent),
                                    'comp_amount': abs(rent.tenant_rent),
                                    'tenant': rent.tenant.id,
                                    'tenant_details': self.id,
                                })
                            else:
                                break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (
                                        rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })
                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (
                                        prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })

                if rent.rent_type == "annual":
                    amount_per_day = rent.tenant_rent / 365
                    months = int(rent.end_date.month) - int(rent.start_date.month)
                    years = int(rent.end_date.year) - int(rent.start_date.year)
                    totalmonths = months + (years * 12)
                    timediff = timedelta(days=365)
                    rent.date = rent.start_date
                    for months in range(totalmonths):
                            prev_date = rent.date
                            rent.date = rent.date + timediff
                            if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                                tenant_rent = self.tenant_property_line.create({
                                    'name': rent.code,
                                    'date': rent.date,
                                    'tent_amount': abs(rent.tenant_rent),
                                    'comp_amount': abs(rent.tenant_rent),
                                    'tenant': rent.tenant.id,
                                    'tenant_details': self.id,
                                })
                            else:
                                break
                    prev_days = monthrange(prev_date.year, prev_date.month)[1]
                    rec_days = monthrange(rent.date.year, rent.date.month)[1]
                    if rent.end_date.year > rent.date.year or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month > 0 or rent.end_date.year == rent.date.year and rent.end_date.month - rent.date.month == 0 and rent.end_date.day > rent.date.day:
                        if rent.end_date.year != rent.date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * rec_days + rent.end_date.day) - (
                                    rent.date.year * 365 + rent.date.month * rec_days + rent.date.day)
                        elif rent.end_date.month != rent.date.month:
                            daysunpaid = (rent.end_date.month * rec_days + rent.end_date.day) - (
                                        rent.date.month * rec_days + rent.date.day)
                        else:
                            daysunpaid = rent.end_date.day - rent.date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })
                    elif rent.end_date.year > prev_date.year or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month > 0 or rent.end_date.year == prev_date.year and rent.end_date.month - prev_date.month == 0 and rent.end_date.day > prev_date.day:
                        if rent.end_date.year != prev_date.year:
                            daysunpaid = (rent.end_date.year * 365 + rent.end_date.month * prev_days + rent.end_date.day) - (
                                    prev_date.year * 365 + prev_date.month * prev_days + prev_date.day)
                        elif rent.end_date.month != prev_date.month:
                            daysunpaid = (rent.end_date.month * prev_days + rent.end_date.day) - (
                                        prev_date.month * prev_days + prev_date.day)
                        else:
                            daysunpaid = rent.end_date.day - prev_date.day
                        totalleft = amount_per_day * daysunpaid
                        tenant_rent = self.tenant_property_line.create({
                            'name': rent.code,
                            'date': rent.end_date,
                            'tent_amount': abs(totalleft),
                            'comp_amount': abs(totalleft),
                            'tenant': rent.tenant.id,
                            'tenant_details': self.id,
                        })
            else:
                if rent.end_date.year > rent.start_date.year or rent.end_date.year == rent.start_date.year and rent.end_date.month - rent.start_date.month > 0 or rent.end_date.year == rent.start_date.year and rent.end_date.month - rent.start_date.month == 0 and rent.end_date.day > rent.start_date.day:
                    tenant_rent = self.tenant_property_line.create({
                        'name': rent.code,
                        'date': rent.end_date,
                        'tent_amount': abs(rent.tenant_rent),
                        'comp_amount': abs(rent.tenant_rent),
                        'tenant': rent.tenant.id,
                        'tenant_details': self.id,
                    })
        return True

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
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.mapped('name'),
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action


class TenantDetailsLine(models.Model):
    _name = 'tenant.details.line'
    _description = 'Tenant Details Line'

    name = fields.Char(compute="_amount_all", readonly=True)
    tenant_details = fields.Many2one("tenant.details", required=True, string="Property")
    start_date_line = fields.Datetime()
    end_date_line = fields.Datetime()
    tent_amount = fields.Float("Rent Amount")
    comp_amount = fields.Float("Compare Amount")
    amount_unchange = fields.Float()
    date = fields.Datetime("Date", readonly=True)
    state = fields.Selection([
            ("unpaid", "Unpaid"),
            ("paid", "Paid"),
        ],
        string="State",
        default="unpaid", required=True, readonly=True,
        )
    t = fields.Float("TT", compute="date_present")
    date_now = fields.Char("Date Passed", default=False, compute="date_present")
    safe = fields.Selection([
            ("date_safe", "Date Safe"),
            ("date_passed", "Date Passed"),
            ("date_confirmed", "Date Confirmed"),
        ],
        string="Safe",
        default="date_safe", required=True,
        )
    tenant = fields.Many2one("res.partner", required=True, string="Tenant", readonly=True)
    line_id = fields.Char("Line Id", compute="add_line_id")
    note = fields.Char("Note")
    count_invoice_amount = fields.Float('Invoice Amount', compute='_count_invoice_amount')
    tax_id = fields.Many2one('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])
    utility = fields.Char('Utility', compute="_amount_all")
    utility_id = fields.Char("Utility Id", compute="add_utility_id")
    utility_price = fields.Float("Utility Total Price")
    terms = fields.Many2one("terms.conditions", string="Terms And Conditions")
    y = fields.Float('YY', compute="_terms_conditions")
    x = fields.Integer()
    z = fields.Integer('ZZ')
    expected_date = fields.Datetime("Expected Date", compute="set_time")

    @api.model
    def date_set(self):
        self.search([
            ('state', '=', 'unpaid'),
            ('date', '<=', fields.Date.to_string(date.today())),
        ]).write({
            'safe': 'date_passed'
        })
        return True

    def date_present(self):
        print("2")
        for line in self:
            print("1")
            prev_days = monthrange(line.date.year, line.date.month)[1]
            rec_days = monthrange(int(datetime.now().strftime("%Y")), int(datetime.now().strftime("%m")))[1]
            now = int(datetime.now().strftime("%Y")) * 365 + int(datetime.now().strftime("%m")) * int(rec_days) + int(datetime.now().strftime("%d"))
            pre = int(int(line.date.year) * 365 + int(line.date.month) * int(prev_days) + int(line.date.day))
            if not line.state == 'unpaid':
                line.date_now = 'Y'
            else:
                line.date_now = 'Z'
            line.t = now - pre
            if line.t >= 0 and line.date_now == 'Z':
                line.update({
                    'safe': 'date_passed',
                })
            else:
                line.update({
                    'safe': 'date_confirmed',
                })
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    def _count_invoice_amount(self):
        for product in self:
            account_move_line_ids = self.env['account.move.line'].search([('name', '=', product.line_id)])
            customer_count = 0.0
            utility = 0.0
            vendor_count = 0.0
            for line in account_move_line_ids:
                if line.move_id.type == "out_invoice" or line.move_id.type == "in_refund":
                    customer_count += line.price_subtotal
                    utility += product.utility_price
                else:
                    vendor_count += line.price_subtotal
            product.count_invoice_amount = customer_count + utility
            product.count_incoming_invoice_amount = vendor_count

    def invoice_amount_button(self):
        self.ensure_one()
        return {
            'name': 'Invoice Amount',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'domain': [('name', '=', self.line_id), ('move_id.type', 'in', ['out_invoice', 'in_refund'])],
        }

    def add_line_id(self):
        for line in self:
            line.line_id = line.name + " For " + str(line.date)

    def add_utility_id(self):
        for line in self:
            line.utility_id = "Utility For " + str(line.date)

    @api.depends('tenant_details.start_date', 'tenant_details.end_date', 'tenant_details.tenant_rent')
    def _amount_all(self):
        for order in self:
            order.update({
                'name': order.tenant_details.code,
                'end_date_line': order.tenant_details.end_date,
                'utility': order.tenant_details.utility,
                'terms': order.tenant_details.terms,
            })
        self.date_present()
        self._terms_conditions()
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    @api.depends('tenant_details.date', 'tenant_details.end_date')
    def _state_change(self):
        for rent in self:
            if rent.tenant_details.date == rent.tenant_details.end_date:
                rent.update({
                    'state': 'paid',
                })

    @api.depends('terms.days')
    def set_time(self):
        for line in self:
            line.expected_date = line.date + timedelta(days=line.terms.days)
    @api.depends('terms.value', 'terms.value_amount', 'terms.days', 'tenant_details.tenant_rent')
    def _terms_conditions(self):
        for line in self:
            prev_days = monthrange(line.date.year, line.date.month)[1]
            rec_days = monthrange(int(datetime.now().strftime("%Y")), int(datetime.now().strftime("%m")))[1]
            now = int(datetime.now().strftime("%Y")) * 365 + int(datetime.now().strftime("%m")) * int(rec_days) + int(datetime.now().strftime("%d"))
            pre = int(int(line.date.year) * 365 + int(line.date.month) * int(prev_days) + int(line.date.day))
            line.y = now - pre
            if line.y <= 0:
                line.z = 4
            if line.y >= line.terms.days and line.tent_amount == line.comp_amount:
                line.z = 3
                if line.terms.value == 'percent':
                    val = line.terms.value_amount * line.tent_amount / 100
                    val = line.tent_amount + val
                    line.tent_amount = val
                    line.z = 1
                elif line.terms.value == 'fixed':
                    val = line.terms.value_amount + line.tent_amount
                    line.tent_amount = val
                    line.z = 1
        return {'type':  'ir.actions.act_close_wizard_and_reload_view'}

