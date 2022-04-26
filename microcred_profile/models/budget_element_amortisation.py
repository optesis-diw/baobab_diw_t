# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr/>)
#              Chris Tribbeck <chris.tribbeck@syleam.fr>
#
#    This file is a part of microcred_profile
#
#    microcred_profile is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    microcred_profile is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import models, api, fields
import odoo.addons.decimal_precision as dp


class BudgetElementAmortisation(models.Model):
    _name = 'budget.element.amortisation'
    _description = 'Budget element amortisation'
    _order = 'date_start asc'

    initial_element_id = fields.Many2one(comodel_name='budget.element', string='Initial element', index=True, required=True, help='The initial element.')
    asset_id = fields.Many2one(comodel_name='account.asset', string='Asset', index=True, help='The asset linked to this')
    date_start = fields.Date(string='Start date', required=True, index=True, help='The start date.')
    date_end = fields.Date(string='End date', required=True, help='The end date.')
    budget_element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='The budget element')
    amount_amortised = fields.Float(string='Amortised amount', digits=("Account"), help='The amortised amount.')
    can_modify = fields.Boolean(string='Can modify the element', compute='_get_can_modify', help='Can modify the element.')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency', related='initial_element_id.company_id.currency_id', readonly=True)

    
    def _get_can_modify(self):
        for element in self:
            element.can_modify = not((element.initial_element_id == element.budget_element_id) and
                                     (element.date_start >= element.initial_element_id.date_start) and
                                     (element.date_end <= element.initial_element_id.date_end))

    @api.model
    def create(self, values):
        ret = super(BudgetElementAmortisation, self).create(values)
        budget_id = ret.initial_element_id
        while budget_id and not budget_id.date_start:
            budget_id = budget_id.budget_id
        if ret.date_start >= budget_id.date_start and ret.date_end <= budget_id.date_end:
            ret.write({
                'budget_element_id': ret.initial_element_id.id,
            })
            ret.initial_element_id.calculate_profit_and_loss()

        return ret

    
    def write(self, values):
        ret = super(BudgetElementAmortisation, self).write(values)
        for amort in self:
            budget_id = amort.initial_element_id
            while budget_id and not budget_id.date_start:
                budget_id = budget_id.budget_id
            if amort.date_start >= budget_id.date_start and amort.date_end <= budget_id.date_end:
                super(BudgetElementAmortisation, self).write({
                    'budget_element_id': amort.initial_element_id.id,
                })
                amort.initial_element_id.calculate_profit_and_loss()

        return ret

    
    def unlink(self):
        return super(BudgetElementAmortisation, self.exists()).unlink()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
