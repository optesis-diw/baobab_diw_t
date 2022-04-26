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

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ExpensifyBudget(models.Model):
    _name = 'expensify.budget'
    _description = 'Expensify budget'
    _order = 'year desc, project_code asc, department_id'
    _sql_constraints = [
        ('year_project_employee_unique', 'unique (year, project_code, department_id, company_id)', 'You cannot create the more than one rule for the same year, project code, department and company!'),
    ]

    year = fields.Integer(string='Year', help='Enter the year', index=True)
    # employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', help='Select the employee', index=True)
    project_code = fields.Char(string='Project code',  help='Enter the project code.', index=True)
    department_id = fields.Many2one(comodel_name='hr.department', string='Department', help='Select the department')
    element_id = fields.Many2one(comodel_name='budget.element', string='Budget Element', help='Select the budget element', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', help='Select the company', required=True)

    @api.constrains('project_code', 'department_id')
    def check_rule_constraint(self):
        if not self.project_code and not self.department_id:
            raise ValidationError(_("You must specify either a project code and/or a department."))

    @api.model
    def get_budget(self, year, project_code, company, employee=None, department=None):
        domain_general = [('year', '=', year), ('company_id', '=', company.id)]
        domain_project = [('project_code', '=', project_code)]
        element = self
        if employee and not department:
            department = employee.department_id

        if department:
            domain_department = [('department_id', '=', department.id)]
            element = self.search(domain_general + domain_project + domain_department)

        if not element:
            element = self.search(domain_general + domain_project)
        if not element and department:
            element = self.search(domain_general + domain_department)
        if element:
            return element.element_id
        return self.env['budget.element']

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
