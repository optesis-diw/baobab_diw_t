# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Chris TRIBBECK <chris.tribbeck@syleam.fr>
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

from odoo import SUPERUSER_ID, api
import logging
logger = logging.getLogger('Update invoiced amount budget')


def migrate(cr, version):
    
    
    with api.Environment.manage():
        uid = SUPERUSER_ID
        ctx = api.Environment(cr, uid, {})['res.users'].context_get()
        env = api.Environment(cr, uid, ctx)

        purchased_amounts = defaultdict(float)
        remove_amounts = defaultdict(float)
        linked_invoice_line_ids = self.env['account.move.line']
            # Calculate from purchase order lines
        purchase_lines = self.env['purchase.order.line'].sudo().search([
                ('budget_element_id', '=', self.id), ('order_id.state', 'in', purchase_order_states)])
        for line in purchase_lines:
            current_rate = 1.0
            if line.order_id.currency_id != self.company_id.currency_id:
                current_rate = line.order_id.currency_id.with_context({'date': line.order_id.date_order, 'company_id': line.order_id.company_id.id}).rate
            purchased_amounts[False] += self.company_id.currency_id.round(line.price_subtotal / current_rate)
            purchased_amounts[y_m_calc(line.date_planned)] += self.company_id.currency_id.round(line.price_subtotal / current_rate)

            linked_invoice_line_ids += line.mapped('invoice_lines')

            # Calculate from move lines
        account_lines = self.env['account.move.line'].sudo().search([
                ('budget_element_id', '=', self.id),
            ], order="debit, credit")
        for line in account_lines:
#             y_m = y_m_calc(line.date)
#             line_amount = (line.debit - line.credit)
#             if line.account_id.code != '48600000' and line.state !='draft':

                invoiced_amounts[False] = 0
                invoiced_amounts[y_m] += 0
              

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
