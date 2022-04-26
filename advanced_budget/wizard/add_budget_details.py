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


class WizardAddBudgetDetailsLine(models.TransientModel):
    _name = "wizard.add.budget.details.line"
    _description = "Add budget details line"

    name = fields.Char(string='Name', size=128, help='Enter the budget element\'s name.', required=True, )
    product_id = fields.Many2one('product.product', string='Product', help='Select the product.')
    amount_fixed = fields.Float(string='Planned amount', digits=(100,2), help='Enter the planned amount.')
    text_distribution = fields.Char(string='Specific distribution', size=128, help='The specific distribution.', compute='_get_text_distribution', )
    original_detail_id = fields.Many2one('budget.element', string='Original detail')
    wizard_id = fields.Many2one('wizard.add.budget.details', string='Wizard')

    
    def _get_text_distribution(self):
        """
        Caclulate the text containing the distribution (if specific).
        """
        for element in self:
            element.text_distribution = "Unknown"

    
    def _make_detail_line_dico(self):
        """
        Create a dictionary for detail (budget.element) generation
        """
        self.ensure_one()
        return {
            'name': self.name,
            'type_id': self.env.ref('advanced_budget.budget_element_type_detail').id,
            'product_id': self.product_id.id,
            'amount_fixed': self.amount_fixed,
        }

    
    def _make_wizard_line_dico(self, detail):
        """
        Create a dictionary for detail (wizard) generation
        """
        detail.ensure_one()
        return {
            'name': detail.name,
            'product_id': detail.product_id.id,
            'amount_fixed': detail.amount_fixed,
            'original_detail_id': detail.id,
        }


class WizardAddBudgetDetails(models.TransientModel):
    _name = "wizard.add.budget.details"
    _description = "Add budget details wizard"

    budget_line_id = fields.Many2one('budget.element', string='Budget line', readonly=True, )
    line_ids = fields.One2many('wizard.add.budget.details.line', 'wizard_id', string='Budget details', help='Add budget details.')

    @api.model
    def default_get(self, fields_list):
        """
        Return budget line information
        """

        values = super(WizardAddBudgetDetails, self).default_get(fields_list)
        wizard_line_obj = self.env['wizard.add.budget.details.line']

        if self.env.context.get('active_model') == 'budget.element':
            values['budget_line_id'] = self.env.context.get('active_id')
            budget_line = self.env['budget.element'].browse(values['budget_line_id'])
            details = []
            for detail in budget_line.budget_detail_ids:
                details.append([0, 0, wizard_line_obj._make_wizard_line_dico(detail)])

            if details:
                values['line_ids'] = details

        return values

    
    def validate(self):
        """
        Validate the details
        """
        for wizard in self:
            details_to_keep = self.line_ids.mapped('original_detail_id')
            details_to_delete = self.env['budget.element'].search([
                ('budget_id', '=', wizard.budget_line_id.id),
                ('type', '=', 'budget_detail'),
            ]) - details_to_keep
            if details_to_delete:
                details_to_delete.unlink()

            new_details = []
            total = 0.0
            for detail in wizard.line_ids:
                detail_dico = detail._make_detail_line_dico()
                if detail.original_detail_id:  # Modify existing
                    detail.original_detail_id.write(detail_dico)
                else:
                    detail_dico['budget_id'] = wizard.budget_line_id.id
                    wizard.budget_line_id.create(detail_dico)
                total += detail.amount_fixed

            if new_details:
                wizard.budget_line_id.write({
                    'amount_fixed': total,
                })


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
