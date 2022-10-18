from odoo import http
from odoo.http import request


class Maintenance(http.Controller):

    @http.route('/maintenance_webform', type="http", auth="user", website=True)
    def patient_webform(self, **kw):
        maintenance_rec = request.env['property.details'].sudo().search([])
        print(maintenance_rec)
        return http.request.render('property_management_system.maintenance_form', {'maintenance_rec': maintenance_rec})

    @http.route('/create/maintenance', type="http", auth="user", website=True)
    def create_webpatient(self, **kw):
        print("Data Received.....", kw)
        request.env['property.maintenance'].sudo().create(kw)
        return request.render("property_management_system.maintenance_thanks", {})


