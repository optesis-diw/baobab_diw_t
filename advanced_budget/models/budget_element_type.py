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

from odoo import models, fields


class BudgetElementType(models.Model):
    _name = ""
    _name = 'budget.element.type'
    _description = 'Budget element type'

    name = fields.Char(string='Name', size=64, help='Budget type name', translate=True, )
    type = fields.Selection([
        ('periodic', 'Periodic'),
        ('project', 'Project'),
        ('budget_line', 'Budget line'),
        ('budget_detail', 'Budget detail'),
        ('department', 'Department'),
        ('partner', 'Partner'),
    ], string=' budget element Type', help='Select the budget element\'s type.', required=True, )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
