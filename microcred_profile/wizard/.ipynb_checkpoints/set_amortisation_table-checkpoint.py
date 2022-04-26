# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Microcred profile
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

from odoo import models, api, fields, _
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare
from collections import defaultdict
from odoo.exceptions import UserError


class WizardSetAmortisationLine(models.TransientModel):
    _name = "wizard.set.amortisation.table.line"
    _description = "Set Amortisation Table Line"
    _order = 'date_start asc'

    wizard_id = fields.Many2one(comodel_name='wizard.set.amortisation.table', string='Wizard')
    date_start = fields.Date(string='Start date', help='The start date.', required=True, index=True, readonly=True)
    date_end = fields.Date(string='End date', help='The end date.', required=True, readonly=True)
    budget_element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='The budget element.')
    profit_loss_amount_fixed = fields.Float(string='P&L Fixed amount', digits=("Account"), help='The P&L fixed amount.')
    can_modify = fields.Boolean(string='Can modify element', default=True)


class WizardSetAmortisation(models.TransientModel):
    _name = "wizard.set.amortisation.table"
    _description = "Set Amortisation Table"

    budget_element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='The budget element.', readonly=True, )
    amount_fixed = fields.Float(string='P&L Fixed amount', digits=("Account"), help='The P&L fixed amount.', related='budget_element_id.amount_fixed', readonly=True)
    line_ids = fields.One2many(comodel_name='wizard.set.amortisation.table.line', inverse_name='wizard_id', string='Amortisation lines')
    data_ok = fields.Boolean(string='Data Ok')

    @api.model
    def default_get(self, fields_list):
        """
        Return budget element information
        """
        values = super(WizardSetAmortisation, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'budget.element' and self.env.context.get('active_id'):
            budget_element = self.env['budget.element'].browse(self.env.context['active_id'])
            values['budget_element_id'] = budget_element.id
            values['line_ids'] = []
            if budget_element.amortisation_element_ids and not budget_element.modification_required:
                for line in budget_element.amortisation_element_ids:
                    values['line_ids'].append((0, 0, {
                        'date_start': line.date_start,
                        'date_end': line.date_end,
                        'profit_loss_amount_fixed': line.amount_amortised,
                        'budget_element_id': line.budget_element_id.id,
                        'can_modify': (line.budget_element_id.id != budget_element.id),
                    }))
                pass
            else:
                lines = budget_element.calculate_amortisation()
                for line in lines:
                    line['profit_loss_amount_fixed'] = line['amount_amortised']
                    line.pop('amount_amortised', 0.0)
                    line['can_modify'] = (line.get('budget_element_id', False) is False)
                    values['line_ids'].append((0, 0, line))
            values['data_ok'] = (self.budget_element_id.state != 'draft')

        return values

    @api.onchange('line_ids.profit_loss_amount_fixed', 'line_ids')
    def onchange_amounts(self):
        if self.budget_element_id.state != 'draft':
            self.data_ok = False
            return
        total = 0.0
        for line in self.line_ids:
            total += line.profit_loss_amount_fixed
        self.data_ok = (float_compare(total, self.amount_fixed, precision_digits=2) == 0)

    
    def validate(self):
        self.ensure_one()
        budget_amounts = defaultdict(float)
        # This bit will reinitialise all budget element amortisations to 0.
        for line in self.budget_element_id.amortisation_element_ids:
            budget_amounts[line.budget_element_id] = 0.0

        new_lines = []
        total = 0.0
        for line in self.line_ids:
            total += line.profit_loss_amount_fixed
            new_lines.append((0, 0, {
                'date_start': line.date_start,
                'date_end': line.date_end,
                'amount_amortised': line.profit_loss_amount_fixed,
                'budget_element_id': line.budget_element_id.id
            }))
            budget_amounts[line.budget_element_id] += line.profit_loss_amount_fixed

        if (float_compare(total, self.amount_fixed, precision_digits=2) != 0):
            raise UserError(_('The total of the amortised lines is not equal to that of the budget line.'))

        self.budget_element_id.amortisation_element_ids.unlink()
        self.budget_element_id.write({
            'amortisation_element_ids': new_lines,
            'profit_loss_amount_fixed': budget_amounts[self.budget_element_id],
            'modification_required': False,
        })
        for budget_element in budget_amounts:
            if budget_element != self.budget_element_id:
                budget_element.write({
                    'profit_loss_amount_fixed': budget_amounts[budget_element],
                })


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
