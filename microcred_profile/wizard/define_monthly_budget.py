# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 Syleam (<http://www.syleam.fr/>)
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


class WizardDefineMonthlyBudgetLine(models.TransientModel):
    _name = 'wizard.define.monthly.budget.line'
    _description = 'Define monthly budget wizard line'

    wizard_id = fields.Many2one('wizard.define.monthly.budget', string='Wizard')
    budget_element_period_id = fields.Many2one('budget.element.period', string='Budget element period')
    period_id = fields.Many2one('account.period', string='Period', help='The period.', related="budget_element_period_id.period_id", readonly=True)
    amount_fixed = fields.Float(string='Fixed amount', digits=("Account"), help='Enter the fixed amount.')
    amount_initial = fields.Float(string='Initial amount', digits=("Account"), help='The initial amount.', readonly=True)
    amount_current = fields.Float(string='Current amount', digits=("Account"), help='The current amount.')
    amount_engaged = fields.Float(string='Engaged amount', digits=("Account"), help='The engaged amount.', readonly=True)
    amount_invoiced = fields.Float(string='Invoiced amount', digits=("Account"), help='The invoiced amount.', readonly=True)
    amount_calculated = fields.Float(string='Calculated amount', digits=("Account"), related='budget_element_period_id.amount_calculated', readonly=True)
    amount_remaining = fields.Float(string='Remaining amount', digits=("Account"), readonly=True)
    period_state = fields.Selection([
        ('open', 'Open'),
        ('partially_closed', 'Partially closed'),
        ('fully_closed', 'Fully closed'),
    ], string='Period\'s state', help='Period\'s state')

    
    def _get_can_compute(self):
        """
        Work out whether we can modify the period or not
        """
        for line in self:
            line.can_edit = line.period_id.date_start > self.env.user.company_id.period_lock_date  # TODO : In multi-company, use the budget element's company id


class WizardDefineMonthlyBudget(models.TransientModel):
    _name = 'wizard.define.monthly.budget'
    _description = 'Define monthly budget wizard'

    budget_element_id = fields.Many2one('budget.element', string='Budget element', help='The budget element.')
    line_ids = fields.One2many('wizard.define.monthly.budget.line', 'wizard_id', string='Period amounts', help='Enter the monthly amounts.')

    @api.model
    def default_get(self, fields_list):
        """
        Return budget line information
        """

        values = super(WizardDefineMonthlyBudget, self).default_get(fields_list)

        if self.env.context.get('active_model') == 'budget.element':
            budget_line = self.env['budget.element'].browse(self.env.context.get('active_id'))

            values['budget_element_id'] = budget_line.id
            details = []
            for period in budget_line.period_detail_ids:
                details.append((0, 0, {
                    'period_id': period.period_id.id,
                    'budget_element_period_id': period.id,
                    'amount_fixed': period.amount_fixed,
                    'amount_engaged': period.amount_engaged,
                    'amount_invoiced': period.amount_invoiced,
                    'amount_remaining': period.amount_remaining,
                    'amount_initial': period.amount_initial,
                    'period_state': period.period_id.state,
                }))
            values['line_ids'] = details

        return values

    
    def validate(self):
        """
        Store the amounts when changed
        """
        for wizard in self:
            total = 0.0
            for period in wizard.line_ids:
                if period.amount_fixed != period.budget_element_period_id.amount_fixed:
                    period.budget_element_period_id.write({
                        'amount_fixed': period.amount_fixed,
                        'has_manual_change': True,
                    })

                total += period.amount_fixed

            wizard.budget_element_id.amount_fixed = total

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
