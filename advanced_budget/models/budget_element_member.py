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


class BudgetElementMember(models.Model):
    _name = 'budget.element.member'
    _description = 'Budget element member'

    user_id = fields.Many2one('res.users', string='User', help='Select the user.', required=True)
    access_level = fields.Selection([
        ('can_select', 'Can select'),
        ('can_modify', 'Can modify'),
    ], string='Access level', help='Select the access level.', required=True, )
    element_id = fields.Many2one('budget.element', string='Budget element', required=True, )


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
