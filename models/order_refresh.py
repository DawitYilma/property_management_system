from odoo import api, fields, models
from importlib import reload

class OrderReload(models.Model):
    _inherit = 'tenant.details'

    def order_reload(self):
        """this method used to reload the order without reload webpage."""
        return {
            'type': 'ir.actions.client',
            'tag': 'trigger_reload'
        }

class OrderLineReload(models.Model):
    _inherit = 'tenant.details.line'

    def order_line_reload(self):
        """this method used to reload the order without reload webpage."""
        self.env["tenant.details"].order_reload()
        #reload(self.tenant.details.line)
        return {
            'type': 'ir.actions.client',
            'target': 'fullscreen',
            'tag': 'reload'
        }


