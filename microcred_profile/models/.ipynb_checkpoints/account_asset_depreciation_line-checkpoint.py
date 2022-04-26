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

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_round, float_compare, float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class AccountAssetDepreciationLine(models.Model):
    _inherit = "account.asset"


    distribution_cost_ids = fields.One2many('budget.element.distribution', 'asset_line_id', string='Cost distribution' )
    can_redistribute = fields.Boolean(string='Can redistribute', compute='_get_can_redistribute', )
    compensation_move_id = fields.Many2one('account.move', string='Accrued Compensation Entry')
    is_accrued_expense = fields.Boolean(string='Accrued expenses', help='If checked, this is accrued expenses.', readonly=True, )
    budget_element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='The budget element', domain=[('type', 'in', ('budget_line', 'budget_detail')), ('subtype', 'in', ('amortised', 'generated'))])
    tag_ids = fields.Many2many(comodel_name='account.analytic.tags', string='asset Tags', deprecated=True, help='tag')
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags17', help='This contains the axis tags for this depreciation line.')

    @api.model
    def create(self, values):
        if values.get('budget_element_id'):
            budget_element = self.budget_element_id.browse(values['budget_element_id'])
            if 'all_tag_ids' not in values:
                # Copy the budget element's tags
                tags = []
                for tag in budget_element.all_tag_ids:
                    tags.append((4, tag.id))
                values['all_tag_ids'] = tags

        return super(AccountAssetDepreciationLine, self).create(values)

    
    def write(self, values):
        if 'budget_element_id' in values:
            recalc_pl_elements = self.mapped('budget_element_id')
            if 'all_tag_ids' not in values:
                budget_element = self.budget_element_id.browse(values['budget_element_id'])
                # Copy the budget element's tags
                tags = []
                for tag in budget_element.all_tag_ids:
                    tags.append((4, tag.id))
                values['all_tag_ids'] = tags

        ret = super(AccountAssetDepreciationLine, self).write(values)
        if 'budget_element_id' in values:
            recalc_pl_elements |= self[0].budget_element_id
            while recalc_pl_elements:
                for element in recalc_pl_elements:
                    element.update_pl_element_amounts()
                recalc_pl_elements = recalc_pl_elements.mapped('budget_id')

        return ret

    
    def _get_can_redistribute(self):
        for asset_line in self:
            asset_line.can_redistribute = not (asset_line.move_check)

    
    def create_accrued_moves(self, post_move=True):
        AccountMove = self.env['account.move']
        created_moves = AccountMove
        for line in self:
            if line.remaining_value > 0.0:
                depreciation_date = self.env.context.get('depreciation_date') or line.depreciation_date or fields.Date.context_today(self)
                compensation_date = (datetime.strptime(depreciation_date, DF) + relativedelta(days=1)).strftime(DF)
                company_currency = line.asset_id.company_id.currency_id
                current_currency = line.asset_id.currency_id
                amount = current_currency.compute(line.amount, company_currency)
                if line.asset_id.category_id.double_entry:
                    amount = current_currency.compute(line.remaining_value, company_currency)
                sign = (line.asset_id.category_id.journal_id.type == 'purchase' or line.asset_id.journal_id.type == 'sale' and 1) or -1
                asset_name = line.asset_id.name + ' (%s/%s)' % (line.sequence, line.asset_id.method_number)
                reference = line.asset_id.code
                journal_id = line.asset_id.journal_id.id
                partner_id = line.asset_id.partner_id.id
                categ_type = line.asset_id.category_id.type
                debit_account = line.asset_id.category_id.account_asset_id.id
                credit_account = line.asset_id.account_accrued_id.id

                # Accrued expense
                move_line_1 = {
                    'name': asset_name,
                    'account_id': debit_account,
                    'debit': 0.0,
                    'credit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency.id or False,
                    'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                    'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'sale' else False,
                    'date': depreciation_date,
                }
                move_line_2 = {
                    'name': asset_name,
                    'account_id': credit_account,
                    'credit': 0.0,
                    'debit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency.id or False,
                    'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                    'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'purchase' else False,
                    'date': depreciation_date,
                }
                move_vals = {
                    'ref': reference + ' ' + _('Accrued expense entry'),
                    'date': depreciation_date or False,
                    'journal_id': line.asset_id.journal_id.id,
                    'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    'asset_id': line.asset_id.id,
                }
                move_1 = AccountMove.create(move_vals)
                created_moves |= move_1

                if line.asset_id.category_id.double_entry:
                    # Compensation -move (the next day)
                    move_line_1 = {
                        'name': asset_name,
                        'account_id': debit_account,
                        'debit': amount,
                        'credit': 0.0,
                        'journal_id': journal_id,
                        'partner_id': partner_id,
                        'currency_id': company_currency != current_currency and current_currency.id or False,
                        'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                        'analytic_account_id': line.asset_id.account_analytic_id.id if categ_type == 'sale' else False,
                        'date': compensation_date,
                    }
                    move_line_2 = {
                        'name': asset_name,
                        'account_id': credit_account,
                        'credit': amount,
                        'debit': 0.0,
                        'journal_id': journal_id,
                        'partner_id': partner_id,
                        'currency_id': company_currency != current_currency and current_currency.id or False,
                        'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                        'analytic_account_id': line.asset_id.account_analytic_id.id if categ_type == 'purchase' else False,
                        'date': compensation_date,
                    }
                    move_vals = {
                        'ref': reference + ' ' + _('Compensation Entry'),
                        'date': compensation_date or False,
                        'journal_id': line.asset_id.category_id.journal_id.id,
                        'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                        'asset_id': line.asset_id.id,
                    }
                    move_2 = AccountMove.create(move_vals)
                    created_moves |= move_2
                else:
                    move_2 = AccountMove

                line.write({
                    'move_id': move_1.id,
                    'compensation_move_id': move_2.id,
                    'move_check': True
                })
            else:
                line.write({
                    'move_check': True
                })

            if line.asset_id.currency_id.is_zero(line.asset_id.value_residual):
                line.asset_id.message_post(body=_("Document closed."))
                line.asset_id.write({'state': 'close'})

        if post_move and created_moves:
            created_moves.filtered(lambda r: r.asset_id and r.asset_id.open_asset).post()
        return [x.id for x in created_moves]

    
    def create_move(self, post_move=True):
        move_obj = self.env['account.move']
        moves_created = []
        for line in self:
            if self._context.get('budget_element_id'):
                line.budget_element_id = self._context['budget_element_id']

            if not line.budget_element_id:
                raise UserError(_("Depreciation lines must be linked to budget elements!"))

            digits_rounding_precision = line.asset_id.company_id.currency_id.rounding
            if line.asset_id.category_id.is_accrued_expense:
                move_created = line.create_accrued_moves(post_move=post_move)
            else:
                move_created = super(AccountAssetDepreciationLine, line.with_context({
                    'swap_accounts': [
                        (line.asset_id.category_id.account_asset_id.id, self._context.get('product_account_id', line.asset_id.product_account_id.id)),
                        (line.asset_id.account_depreciation_id.id, line.asset_id.account_asset_id.id)
                    ]
                })).create_move(post_move=post_move)

            for move in move_obj.browse(move_created):
                # Manage the asset sale date
                if self._context.get('date_sold'):
                    move.date = self._context['date_sold']
                    for move_line in move.line_ids:
                        move_line.date = self._context['date_sold']

                for move_line in move.line_ids:
                    amount = move_line.debit  # Change to debit if necessary
                    move_line_dict = {}
                    if move_line.account_id.authorise_analytics:
                        if line.budget_element_id.all_tag_ids:
                            # Copy axis
                            tags = [(5, 0, 0)]
                            for tag in line.budget_element_id.all_tag_ids:
                                tags.append((4, tag.id))
                            move_line_dict.update({
                                'all_tag_ids': tags,
                            })
                        elif line.asset_id.invoice_line_id.all_tag_ids:
                            # Copy axis
                            tags = [(5, 0, 0)]
                            for tag in line.asset_id.invoice_line_id.all_tag_ids:
                                tags.append((4, tag.id))
                            move_line_dict.update({
                                'all_tag_ids': tags,
                            })

                    if amount:
                        # Create distributions
                        distribution_cost_ids = line.distribution_cost_ids
                        coefficient = 1.0
                        if line.distribution_cost_ids:
                            distribution_cost_ids = line.distribution_cost_ids
                        elif line.asset_id.invoice_line_id:  # Get the distribution from the invoice
                            distribution_cost_ids = line.asset_id.invoice_line_id.get_distribution_cost_ids()
                            coefficient = line.asset_id.invoice_line_id.price_subtotal and (amount / line.asset_id.invoice_line_id.price_subtotal) or 0.0
                        distribution_costs = []
                        if distribution_cost_ids and move_line.account_id.authorise_analytics:
                            # Create fixed distribution costs for this move line and there's no asset depreciation
                            amount_calculated = 0.
                            highest_price_calculated = False
                            price_calculated = 0.
                            costs_dico = {}
                            for distribution_cost in distribution_cost_ids:
                                if distribution_cost.percentage:
                                    price_calculated = float_round(amount * distribution_cost.percentage / 100., precision_rounding=digits_rounding_precision)
                                    amount_calculated += price_calculated
                                elif distribution_cost.amount_fixed:
                                    if float_compare(distribution_cost.amount_fixed * coefficient, amount, precision_rounding=digits_rounding_precision) == 1:
                                        raise UserError(_("It is impossible to allocate the amount of %f in the line %s.\n\nPlease make a allocation manually") % (distribution_cost.amount_fixed, line.name))

                                    price_calculated = float_round(distribution_cost.amount_fixed, precision_rounding=digits_rounding_precision)
                                    amount_calculated += price_calculated

                                costs_dico[distribution_cost] = price_calculated

                                if float_compare(price_calculated, highest_price_calculated, precision_rounding=digits_rounding_precision) == 1:
                                    highest_price_calculated = distribution_cost

                            if float_compare(amount, amount_calculated, precision_rounding=digits_rounding_precision):
                                # We have a rounding error - apply it to the highest distribution cost
                                amount_residual = amount - amount_calculated
                                if highest_price_calculated:
                                    costs_dico[highest_price_calculated] += amount_residual

                            for distribution_cost in distribution_cost_ids:
                                distribution_costs.append((0, 0, {
                                    'budget_partner_id': distribution_cost.child_id.id,
                                    'amount_fixed': costs_dico[distribution_cost],
                                    'asset_line_id': line.id,
                                }))

                        move_line_dict.update({
                            'budget_element_id': line.budget_element_id.id,
                            'invoice_line_id': line.asset_id.invoice_line_id.id,
                        })

                        if distribution_costs:
                            move_line_dict['distribution_partner_ids'] = distribution_costs

                    if move_line_dict:
                        move_line.write(move_line_dict)

            moves_created.extend(move_created)

        return moves_created


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
