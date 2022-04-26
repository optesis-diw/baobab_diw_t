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


class WizardModifyInvoiceBudgetLine(models.TransientModel):
    _name = 'wizard.modify.invoice.budget.line'
    _description = "Modify invoice budget line wizard"

    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line', help='The selected invoice line', required=True, )
    budget_element_id = fields.Many2one('budget.element', string='Budget element', help='Select the budget element', required=True, )

    @api.model
    def default_get(self, fields_list):
        """
        Return budget element information
        """
        values = super(WizardModifyInvoiceBudgetLine, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'account.move.line' and self.env.context.get('active_id'):
            values['invoice_line_id'] = self.env.context.get('active_id')
            values['budget_element_id'] = self.env['account.move.line'].browse(values['invoice_line_id']).budget_element_id.id

        return values

    
    def validate(self):
        self.ensure_one()

        if self.invoice_line_id:
            recalc_budget_element = self.invoice_line_id.budget_element_id | self.budget_element_id
            self.invoice_line_id.write({'budget_element_id': self.budget_element_id.id})
            move_lines = self.env['account.move.line'].search([('invoice_line_id', '=', self.invoice_line_id.id)])
            if move_lines:
                move_lines.with_context({'no_budget_element_transfer': True}).write({'budget_element_id': self.budget_element_id.id})
            recalc_budget_element.calculate_amounts()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
