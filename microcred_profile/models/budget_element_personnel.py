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

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class BudgetElementPersonnel(models.Model):
    _name = "budget.element.personnel"
    _description = "Budget element personnel"

    budget_id = fields.Many2one('budget.element', string='Budget')
    budget_line_id = fields.Many2one('budget.element', string='Budget line')  # , domain=[('type', 'in', ('budget_line', 'budget_detail')), '|', ('budget_id', '=', budget_id), ('budget_id.budget_id', '=', budget_id)])
    employee_id = fields.Many2one('hr.employee', string='Employee', help='Select the employee.', required=True, )
    days = fields.Float(string='Days', digits=("Account"), help='Enter the number of days this employee is required.')
    unit_price = fields.Float(string='Unit price', digits=("Account"), help='The unit price of this employee', related="employee_id.timesheet_price", readonly=True, )
    price_subtotal = fields.Float(string='Subtotal', digits=("Account"), help='The cost of this employee', compute='_get_subtotal', )
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency', related='budget_id.company_id.currency_id', readonly=True)

    
    def _get_subtotal(self):
        for employee in self:
            employee.price_subtotal = employee.days * employee.unit_price

    @api.model
    def create(self, values):
        """
        If there is no budget element, attach it to the personnel budget line (creating it if necessary)
        """
        new_record = super(BudgetElementPersonnel, self).create(values)
        if 'budget_line_id' not in values:
            new_record.budget_id.check_personnel()

        return new_record

    
    def write(self, values):
        """
        If there is no budget element, attach it to the personnel budget line (creating it if necessary)
        """
        budgets_to_check = self.env['budget.element']
        if 'budget_line_id' in values or 'budget_id' in values:
            budgets_to_check = budgets_to_check.search([('id', 'in', self.mapped('budget_id.id'))])
        ret = super(BudgetElementPersonnel, self).write(values)
        budgets_to_check |= budgets_to_check.search([('id', 'in', self.mapped('budget_id.id'))])
        budgets_to_check.check_personnel()

        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
