# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.syleam.fr/>)
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
from odoo.tools.translate import _
from odoo.exceptions import UserError


class WizardReaffectBudgetLine(models.TransientModel):
    _name = "wizard.reaffect.budget.line"
    _description = "Reaffect budget line for wizard"

    wizard_id = fields.Many2one(comodel_name='wizard.reaffect.budget', string='Wizard')
    element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='The budget element to reaffect.')
    #state = fields.Selection([
    #    ('draft', 'Draft'),
    #    ('proposition', 'Proposition'),
    #    ('open', 'Open'),
    #    ('done', 'Closed'),
    #    ('cancel', 'Cancelled'),
    #], string='State', help='The budget element\'s state.', readonly=True, related='element_id.state')
    state = fields.Selection(string='State', help='The budget element\'s state.', readonly=True, related='element_id.state')
    #type = fields.Selection([
    #   ('periodic', 'Periodic'),
    #    ('project', 'Project'),
    #    ('budget_line', 'Budget line'),
    #    ('budget_detail', 'Budget detail'),
    #    ('department', 'Department'),
    #    ('partner', 'Partner'),
    # ], string=' Type', related='element_id.type_id.type', readonly=True)
    #migration by yowit ctd --selection related 
    type = fields.Selection(string='Type', related='element_id.type_id.type', readonly=True)


class WizardReaffectBudget(models.TransientModel):
    _name = "wizard.reaffect.budget"
    _description = "Reaffect budget wizard"

    budget_element_id = fields.Many2one(comodel_name='budget.element', string='New budget element', required=True)
    line_ids = fields.One2many(comodel_name='wizard.reaffect.budget.line', inverse_name='wizard_id', string='Elements to change', help='Select the elements to change')
    data_ok = fields.Boolean(string='Data OK', default=False)
    errors = fields.Text(string='Errors', help='The list of errors', readonly=True)
    date_start = fields.Date(string='Start date', help='The start date of the budget.')
    date_end = fields.Date(string='End date', help='The end date of the budget.')

    @api.onchange('line_ids', 'budget_element_id')
    def onchange_element_ids(self):
        date_start = False
        date_end = False
        error_list = {}
        for line in self.line_ids:
            element = line.element_id
            if date_start and (date_start != element.date_start or date_end != element.date_end):
                error_list['element_date'] = _('Elements must have the same dates')
            else:
                date_start = element.date_start
                date_end = element.date_end

            if element.state != 'draft':
                error_list['element_state'] = _('Only draft budget elements can be reaffected')

            if element.type not in ('budget_line', 'budget_detail'):
                error_list['element_type'] = _('Only budget lines and details can be reaffected')

            if self.budget_element_id:
                if element.has_details and self.budget_element_id.type == 'budget_line':
                    error_list['type_detail'] = _('You cannot affect a budget line with details to another budget line')
                if element == self.budget_element_id:
                    error_list['self_affectation'] = _('You cannot affect a budget line to itself')

        if self.budget_element_id:
            if self.budget_element_id.state != 'draft':
                error_list['parent_state'] = _('Elements can be reaffected only to draft budgets')
            if 'element_date' not in error_list and (self.budget_element_id.date_start != date_start or self.budget_element_id.date_end != date_end):
                error_list['parent_date'] = _('The budget receiving these elements must have the same date')

        update_data = {}
        if 'element_date' not in error_list:
            update_data.update({
                'date_start': date_start,
                'date_end': date_end
            })
        else:
            update_data.update({
                'date_start': False,
                'date_end': False
            })

        if error_list:
            update_data.update({
                'errors': ',\n'.join(error_list.values()),
                'data_ok': False
            })
        else:
            update_data.update({
                'errors': False,
                'data_ok': True
            })

        self.update(update_data)

    @api.model
    def default_get(self, fields_list):
        """
        Get the element ids
        """

        values = super(WizardReaffectBudget, self).default_get(fields_list)

        if self.env.context.get('active_ids'):
            lines = []
            model = self.env.context.get('active_model')
            if model == 'budget.element':
                for line in self.env[model].browse(self.env.context.get('active_ids')):
                    lines.append((0, 0, {
                        'element_id': line.id,
                        'state': line.state,
                        'type': line.type
                    }))
                values['line_ids'] = lines
            else:
                raise UserError(_('The model type \'%s\' is not managed.') % self.env.context.get('active_model'))

        return values

    
    def validate(self):
        self.ensure_one()

        new_type = self.env.ref('advanced_budget.budget_element_type_line')
        if self.budget_element_id.type == 'budget_line':
            # Recasting as detail
            new_type = self.env.ref('advanced_budget.budget_element_type_detail')

        self.line_ids.mapped('element_id').write({
            'budget_id': self.budget_element_id.id,
            'type_id': new_type.id,
            'state': self.budget_element_id.state,
        })


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
