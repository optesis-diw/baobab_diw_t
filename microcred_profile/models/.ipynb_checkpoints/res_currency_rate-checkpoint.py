# -*- coding: utf-8 -*-
# Copyright 2017 SYLEAM Info Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models


class res_currency_rate(models.Model):
    _inherit = "res.currency.rate"

    @api.model
    def create(self, values):

        currency = self.env['res.currency'].browse(values.get('currency_id', self.env.context.get('default_currency_id')))

        if not currency.update:
            values['rate'] = currency.with_context({'company_id': values['company_id']}).rate

        ret = super(res_currency_rate, self).create(values)

        return ret
