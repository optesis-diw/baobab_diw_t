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

from odoo import models, api, fields, exceptions


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    budget_element_id = fields.Many2one('budget.element', string='Budget element', help='Select the budget element', domain=[('type', 'in', ('budget_line', 'budget_detail')), ('linked_distribution_id', '=', False)])
    distribution_cost_ids = fields.One2many('budget.element.distribution', 'sale_line_id', string='Cost distribution')

    
    def copy(self, default=None):
        """
        If the budget element is no longer open, remove it from the purchase order
        """
        self.ensure_one()
        default = dict(default or {})
        if self.budget_element_id.state not in ('open'):
            default['budget_element_id'] = False

        return super(SaleOrderLine, self).copy(default=default)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
