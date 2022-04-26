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
from odoo.exceptions import UserError


class WizardAddBudgetDetailsLine(models.TransientModel):
    _inherit = "wizard.add.budget.details.line"

    date_planned = fields.Date(string='Date planned', help='Enter the planned date of this expense.')
    amortisation_time = fields.Float(string='Amortisation time', digits=("Account"), help='The time for amortisation (months).')
    amortisation_date = fields.Date(string='Amortisation date', help='The date of the start of amortisation.')
    programme_tag_ids = fields.Many2many(comodel_name='budget.element.tag', relation='detail_wizard_programme_tag_rel', domain=[('type', '=', 'programme')], string='Programme tag', help='')
    finance_tag_ids = fields.Many2many(comodel_name='budget.element.tag', relation='detail_wizard_finance_tag_rel', domain=[('type', '=', 'finance')], string='Finance tag', help='')
    tag_ids = fields.Many2many(comodel_name='budget.element.tag', domain=[('type', '=', 'other')], string='Other tag', help='')
    axis_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string=' Axis tags29 for the budget element', help='This contains the axis tags for this budget element.')
    exists = fields.Boolean(string='Exists')
    budget_line_type_id = fields.Many2one('budget.line.type', string='Line type', help='Select the budget line type.')

    
    def _make_detail_line_dico(self):
        ret = super(WizardAddBudgetDetailsLine, self)._make_detail_line_dico()
        ret.update({
            'date_planned': self.date_planned,
            'amortisation_time': self.amortisation_time,
            'amortisation_date': self.amortisation_date,
            'tag_ids': (self.tag_ids and [(6, 0, self.tag_ids.ids)]) or (not self.exists and self.wizard_id.budget_line_id.tag_ids and [(6, 0, self.wizard_id.budget_line_id.tag_ids.ids)]) or [],
            'axis_tag_ids': (self.axis_tag_ids and [(6, 0, self.axis_tag_ids.ids)]) or (not self.exists and self.wizard_id.budget_line_id.axis_tag_ids and [(6, 0, self.wizard_id.budget_line_id.axis_tag_ids.ids)]) or [],
            'finance_tag_ids': (self.finance_tag_ids and [(6, 0, self.finance_tag_ids.ids)]) or (not self.exists and self.wizard_id.budget_line_id.finance_tag_ids and [(6, 0, self.wizard_id.budget_line_id.finance_tag_ids.ids)]) or [],
            'programme_tag_ids': (self.programme_tag_ids and [(6, 0, self.programme_tag_ids.ids)]) or (not self.exists and self.wizard_id.budget_line_id.programme_tag_ids and [(6, 0, self.wizard_id.budget_line_id.programme_tag_ids.ids)]) or [],
            'budget_line_type_id': self.budget_line_type_id.id,
        })
        return ret

    
    def _make_wizard_line_dico(self, detail):
        """
        Create a dictionary for detail (wizard) generation
        """
        ret = super(WizardAddBudgetDetailsLine, self)._make_wizard_line_dico(detail)
        ret.update({
            'date_planned': detail.date_planned,
            'amortisation_time': detail.amortisation_time,
            'amortisation_date': detail.amortisation_date,
            'tag_ids': detail.tag_ids and [(6, 0, detail.tag_ids.ids)] or [],
            'axis_tag_ids': detail.axis_tag_ids and [(6, 0, detail.axis_tag_ids.ids)] or [],
            'finance_tag_ids': detail.finance_tag_ids and [(6, 0, detail.finance_tag_ids.ids)] or [],
            'programme_tag_ids': detail.programme_tag_ids and [(6, 0, detail.programme_tag_ids.ids)] or [],
            'exists': True,
            'budget_line_type_id': detail.budget_line_type_id.id,
        })
        return ret

    @api.onchange('budget_line_type_id')
    def onchange_budget_line_type(self):
        if self.budget_line_type_id:
            self.name = self.budget_line_type_id.name
            axis_rem_list = []
            tag_add_list = []
            for tag in self.budget_line_type_id.tag_ids:
                axis_rem_list.append(tag.axis)
                tag_add_list.append(tag.id)

            for tag in self.axis_tag_ids:
                if tag.axis not in axis_rem_list:
                    tag_add_list.append(tag.id)

            self.axis_tag_ids = [(6, 0, tag_add_list)]


class WizardAddBudgetDetails(models.TransientModel):
    _inherit = "wizard.add.budget.details"

    default_budget_line_type_id = fields.Many2one('budget.line.type', string='Line type', help='Select the budget line type.')

    @api.model
    def default_get(self, fields_list):
        """
        Return budget line information
        """
        raise UserError(_('This assistant should no longer be visible - please contact IT about this (it was not taken out in case it displays somewhere...)'))

        values = super(WizardAddBudgetDetails, self).default_get(fields_list)

        if self.env.context.get('active_model') == 'budget.element':
            budget_line = self.env['budget.element'].browse(values['budget_line_id'])

            values['amount_fixed'] = budget_line.amount_fixed
            values['default_budget_line_type_id'] = budget_line.budget_line_type_id.id

        return values


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
