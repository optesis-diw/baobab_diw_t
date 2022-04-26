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

from odoo import models, api, fields
import odoo.addons.decimal_precision as dp


class WizardViewBudgetElement(models.TransientModel):
    _name = 'wizard.view.budget.element'
    _description = "View budget element wizard"

    budget_element_id = fields.Many2one('budget.element', string='Budget element', help='Select the budget element', required=True, readonly=True)
    amount_invoiced = fields.Float(string='Amount invoiced', digits=("Account"), help='The amount invoiced.', related='budget_element_id.amount_invoiced', readonly=True)
    amount_engaged = fields.Float(string='Amount engaged', digits=("Account"), help='The amount engaged.', related='budget_element_id.amount_engaged', readonly=True)
    amount_fixed = fields.Float(string='Amount planned', digits=("Account"), help='The amount planned.', related='budget_element_id.amount_fixed', readonly=True)
    amount_remaining = fields.Float(string='Amount remaining', digits=("Account"), help='The amount remaining.', related='budget_element_id.amount_remaining', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """
        Return budget element information
        """
        values = super(WizardViewBudgetElement, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'account.move.line' and self.env.context.get('active_id'):
            values['budget_element_id'] = self.env['account.move.line'].browse(self.env.context.get('active_id')).budget_element_id.id
        elif self.env.context.get('active_model') == 'purchase.order.line' and self.env.context.get('active_id'):
            values['budget_element_id'] = self.env['purchase.order.line'].browse(self.env.context.get('active_id')).budget_element_id.id

        return values

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
