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

from odoo import models, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    @api.model
    def create(self, vals):
        """
        Create the budget element associated with this department
        """

        new_department = super(HrDepartment, self).create(vals)
        budget_vals = {
            'name': new_department.name,
            'type_id': self.env.ref('advanced_budget.budget_element_type_department').id,
            'department_id': new_department.id,
        }
        self.env['budget.element'].create(budget_vals)

        return new_department


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
