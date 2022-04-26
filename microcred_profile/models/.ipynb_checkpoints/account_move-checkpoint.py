# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr/>)
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
import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta
from collections import defaultdict, namedtuple



class AccountMove(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin', 'account.move']
    _name = 'account.move'

    child_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags8', store=True, compute='_compute_child_tag_ids',
                                     relation='account_move_child_tag_rel', help='This contains the axis tags for this journal entry\'s lines.')
    state = fields.Selection(tracking=True)
    amount = fields.Monetary(tracking=True)
    
   

    @api.depends(
        'line_ids.all_tag_ids'
    )
    def _compute_child_tag_ids(self):
        for entry in self:
            entry.child_tag_ids = [(6, 0, entry.mapped('line_ids.all_tag_ids').ids)]
    
    
    def _update_child_tag_ids(self):
        invoice_lines = env['account.move.line'].search([('tag_ids', '!=', False), ('move_id.company_id', '=', company.id)])
        for line in invoice_lines:
            line.child_tag_ids = [(6, 0, entry.mapped('line_ids.all_tag_ids').ids)]

    
    def post(self):
        for move in self:
            payroll = self.env['hr.import.payroll'].sudo().search([('move_id', '=', move.id)])
            if payroll:
                payroll.state = 'done'

        return super(AccountMove, self).post()

    
    def button_cancel(self):
        ret = super(AccountMove, self).button_cancel()
        for move in self:
            move.message_post(body=_('Journal entry cancelled'))
        return ret
    
    
    
    
    
    
    
    ##Ajout budget line dans formulaire depense differe##
#     @api.model
#     def _prepare_move_for_asset_depreciation(self, vals):
#         missing_fields = set(['asset_id', 'move_ref', 'amount', 'asset_remaining_value', 'asset_depreciated_value']) - set(vals)
#         if missing_fields:
#             raise UserError(_('Some fields are missing {}').format(', '.join(missing_fields)))
#         asset = vals['asset_id']
#         account_analytic_id = asset.account_analytic_id
#         analytic_tag_ids = asset.analytic_tag_ids
#         depreciation_date = vals.get('date', fields.Date.context_today(self))
#         company_currency = asset.company_id.currency_id
#         current_currency = asset.currency_id
#         prec = company_currency.decimal_places
#         amount_currency = vals['amount']
#         amount = current_currency._convert(amount_currency, company_currency, asset.company_id, depreciation_date)
#         # Keep the partner on the original invoice if there is only one
#         partner = asset.original_move_line_ids.mapped('partner_id')
#         partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
#         if asset.original_move_line_ids and asset.original_move_line_ids[0].move_id.move_type in ['in_refund', 'out_refund']:
#             amount = -amount
#             amount_currency = -amount_currency
#         move_line_1 = {
#             'name': asset.name,
#             'partner_id': partner.id,
#             'account_id': asset.account_depreciation_id.id,
#             'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
#             'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
#             'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
#             'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
#             'currency_id': current_currency.id,
#             'amount_currency': -amount_currency,
#         }
#         move_line_2 = {
#             'name': asset.name,
#             'partner_id': partner.id,
#             'account_id': asset.account_depreciation_expense_id.id,
#             'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
#             'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
#             'analytic_account_id': account_analytic_id.id if asset.asset_type in ('purchase', 'expense') else False,
#             'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in ('purchase', 'expense') else False,
#             'currency_id': current_currency.id,
#             'amount_currency': amount_currency,
#         }
#         move_vals = {
#             'ref': vals['move_ref'],
#             'partner_id': partner.id,
#             'date': depreciation_date,
#             'journal_id': asset.journal_id.id,
#             'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
#             'asset_id': asset.id,
#             'asset_remaining_value': vals['asset_remaining_value'],
#             'asset_depreciated_value': vals['asset_depreciated_value'],
#             'amount_total': amount,
#             'name': '/',
#             'asset_value_change': vals.get('asset_value_change', False),
#             'move_type': 'entry',
#             'currency_id': current_currency.id,
#             'budget_element_id': budget_element_id,
#         }
#         return move_vals

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
