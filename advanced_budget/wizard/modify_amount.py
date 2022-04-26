# -*- coding: utf-8 -*-
##############################################################################
#
#    advanced_budget module for odoo, Advanced budgets
#    Copyright (C) 2016 Syleam (<http://www.syleam.fr/>)
#              Chris Tribbeck <chris.tribbeck@syleam.fr>
#
#    This file is a part of advanced_budget
#
#    advanced_budget is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    advanced_budget is distributed in the hope that it will be useful,
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
from odoo.tools.translate import _
from odoo.exceptions import UserError


class WizardModifyAmountDetails(models.TransientModel):
    _name = 'wizard.modify.amount.detail'
    _description = 'Modify amount detail line'

    budget_detail_id = fields.Many2one('budget.element', string='Budget detail', readonly=True, required=True, )
    amount = fields.Float(string='New amount', digits=(100,2), help='Enter the new amount.')
    wizard_id = fields.Many2one('wizard.modify.amount', string='Wizard')


class WizardModifyAmount(models.TransientModel):
    _name = "wizard.modify.amount"
    _description = "Modify amount wizard"

    budget_line_id = fields.Many2one('budget.element', string='Budget line', readonly=True, required=True, )
    amount = fields.Float(string='New amount',digits=(100,2), help='Enter the new amount.')
    max_amount = fields.Float(string='Max amount', digits=(100,2), help='The maximum amount.')
    budget_detail_ids = fields.One2many('wizard.modify.amount.detail', 'wizard_id', string='Budget details', help='Enter the new amounts for the details.')
    has_details = fields.Boolean(string='Has details')

    @api.model
    def default_get(self, fields_list):
        """
        Return budget line information
        """

        values = super(WizardModifyAmount, self).default_get(fields_list)

        if self.env.context.get('active_model') == 'budget.element':
            values['budget_line_id'] = self.env.context.get('active_id')
            budget_line = self.env['budget.element'].browse(values['budget_line_id'])
            values['amount'] = budget_line.amount_fixed
            total_calculated = 0.0
            main_budget = False
            if budget_line.type == 'budget_line':
                main_budget = budget_line.budget_id
            elif budget_line.type == 'budget_detail':
                main_budget = budget_line.budget_id.budget_id

            if main_budget:
                for line in main_budget.budget_line_ids:
                    if line.budget_detail_ids:
                        for detail in line.budget_detail_ids:
                            total_calculated += detail.amount_fixed
                    else:
                        total_calculated += line.amount_fixed
                if budget_line.budget_detail_ids:
                    details = []
                    for detail in budget_line.budget_detail_ids:
                        details.append((0, 0, {
                            'budget_detail_id': detail.id,
                            'amount': detail.amount_fixed
                        }))
                    values['budget_detail_ids'] = details
                    values['has_details'] = True
                else:
                    values['has_details'] = False

                values['max_amount'] = main_budget.amount_fixed - total_calculated + values['amount']

        return values

    
    def validate(self):
        """
        Validate the amount change
        """
        for wizard in self:
            # If there are details, calculate the new total
            if wizard.budget_detail_ids:
                amount = 0.0
                for detail in wizard.budget_detail_ids:
                    amount += detail.amount
                    min_allowed = (detail.budget_detail_id.amount_fixed or detail.budget_detail_id.amount_calculated) - detail.budget_detail_id.amount_remaining
                    if detail.amount < min_allowed:
                        raise UserError(_('You cannot put less than %.2f (the amounts engaged and/or invoiced) for the detail \'%s\'.') % (min_allowed, detail.budget_detail_id.name))

                wizard.amount = amount
            # Check that the total won't be too high
            min_allowed = (wizard.budget_line_id.amount_fixed or wizard.budget_line_id.amount_calculated) - wizard.budget_line_id.amount_remaining
            if wizard.amount < min_allowed:
                raise UserError(_('You cannot put less than %.2f (the amounts engaged and/or invoiced) for the line.') % min_allowed)

            main_budget = False
            if wizard.budget_line_id.type == 'budget_line':
                max_allowed = wizard.max_amount
                min_allowed = -1.0
                if wizard.budget_line_id.type != 'budget_detail':
                    for detail in wizard.budget_line_id.budget_id.budget_detail_ids:
                        min_allowed += detail.amount_fixed

                if wizard.amount > max_allowed:
                    raise UserError(_('You cannot put more than %.2f (the total budget minus the sum of the other lines).') % max_allowed)

                if wizard.amount < min_allowed:
                    raise UserError(_('You cannot put less than %.2f (the sum of the details).') % min_allowed)


            old_amounts = {}
            new_amounts = {}
            for detail in wizard.budget_detail_ids:
                old_amounts[detail] = detail.budget_detail_id.amount_fixed
                new_amounts[detail] = detail.amount
                detail.budget_detail_id.write({
                    'amount_fixed': detail.amount,
                })

            old_amount = wizard.budget_line_id.amount_fixed
            wizard.budget_line_id.write({
                'amount_fixed': wizard.amount,
            })

            main_budget = wizard.budget_line_id
            if wizard.budget_line_id.budget_id:
                main_budget = wizard.budget_line_id.budget_id

            line_type = ''
            if main_budget:
                if main_budget.state == 'proposition':
                    line_type = _('Proposition:') + ' '
                if wizard.budget_line_id.type == 'budget_line':
                    message = _('%sBudget line \'%s\' modified from %.2f to %.2f') % (line_type, wizard.budget_line_id.name, old_amount, wizard.amount)
                else:
                    message = _('%sBudget \'%s\' modified from %.2f to %.2f') % (line_type, wizard.budget_line_id.name, old_amount, wizard.amount)
                details = []
                if wizard.budget_detail_ids:
                    for detail in wizard.budget_detail_ids:
                        if old_amounts[detail] != new_amounts[detail]:
                            details.append(_('Detail \'%s\' modified from %.2f to %.2f') % (detail.budget_detail_id.name, old_amounts[detail], new_amounts[detail]))

                    if details:
                        message += _(':<br/>\n&#160;&#160;&#160;&#160;&#8211;&#160;') + '<br/>\n&#160;&#160;&#160;&#160;&#8211;&#160;'.join(details)
                main_budget.message_post(body=message)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
