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


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

#     budget_element_id = fields.Many2one('budget.element', string='Budget element', help='Select the budget element', domain=[('type', 'in', ('budget_line', 'budget_detail')), ('linked_distribution_id', '=', False)])
    budget_element_id = fields.Many2one('budget.element',related='purchase_line_id.budget_element_id', string='Budget element',store=False)
    distribution_cost_ids = fields.One2many('budget.element.distribution', 'invoice_line_id', string='Cost distribution' )

    @api.depends('purchase_line_id') 
    def _get_budget(self):
        self.budget_element_id = self.purchase_line_id.budget_element_id
        
    def _set_additional_fields(self, invoice):

        ret = super(AccountInvoiceLine, self)._set_additional_fields(invoice)

        for line in self:
            line.budget_element_id = line.purchase_line_id.budget_element_id.id

        return ret


    def copy(self, default=None):
        """
        If the budget element is no longer open, remove it from the purchase order
        """
        self.ensure_one()
        default = dict(default or {})
        if self.budget_element_id.state not in ('open'):
            default['budget_element_id'] = True
        else:
            default['budget_element_id'] = True

        return super(AccountInvoiceLine, self).copy(default=default)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
