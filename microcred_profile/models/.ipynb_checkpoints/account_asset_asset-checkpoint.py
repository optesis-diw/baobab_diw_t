# -*- coding: utf-8 -*-
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


from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from collections import defaultdict
from odoo.exceptions import UserError
from odoo.tools import float_round, float_compare


class AccountAssetAsset(models.Model):
    
    _inherit = 'account.asset'


    invoice_line_id = fields.Many2one('account.move.line', string='Invoice line')
    accrued_date_end = fields.Date(string='Accrued end date', help='The end date for accrued expenses.')
    is_accrued_expense = fields.Boolean(string='Accrued expenses', help='If checked, this is accrued expenses.', readonly=True, )
    end_of_month = fields.Boolean(string='End of month', help='Generate movements at the end of the month.', readonly=True, )
    account_accrued_id = fields.Many2one('account.account', string='Accrued Expense Account', required=True, domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    daily_prorata = fields.Boolean(string='Daily Prorata', help='Check if the prorata amount is to be calculated on a daily basis.', readonly=True,)
    product_account_id = fields.Many2one(comodel_name='account.account', string='Product account', help='Select thet product\'s account.')
    credit_note_move_id = fields.Many2one(comodel_name='account.move', string='Credit note', help='Credit note move', readonly=True, )
    element_amortisation_ids = fields.One2many(comodel_name='budget.element.amortisation', inverse_name='asset_id', string='Budget element amortisation', help='Element amortisation lines.')
    budget_element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='The main budget element.')

    @api.onchange('date', 'accrued_date_end')
    def onchange_accrued_date_end(self):
        # Calculate the number of periods (method_number)
        if self.is_accrued_expense and self.date and self.accrued_date_end:
            date_start = datetime.strptime(self.date, DF) + relativedelta(day=1)  # 1st of the month
            date_end = datetime.strptime(self.accrued_date_end, DF) + relativedelta(day=1) + relativedelta(months=1, days=-1)  # Last day of the month
            delta = relativedelta(date_end, date_start)
            months = abs(delta.years * 12 + delta.months)
            self.method_number = months + 1

    @api.model
    def create(self, values):
        if values.get('invoice_line_id'):
            invoice_line = self.env['account.move.line'].browse(values['invoice_line_id'])
            if invoice_line.budget_element_id:
                values['budget_element_id'] = invoice_line.budget_element_id.id
        elif values.get('move_id'):
            raise UserError(_("Internal error.\n\nFor some reason, the invoice line was not transferred to the asset (it's not your fault !) - please contact the person(s) in charge of Odoo, so that they can see why this happened!"))

        new_asset = super(AccountAssetAsset, self).create(values)
        new_vals = {}
        if new_asset.is_accrued_expense:
            new_vals = {
                'method_number': 1,
                'daily_prorata': new_asset.daily_prorata,
            }
            if new_asset.invoice_line_id:
                new_vals.update({
                    'account_accrued_id': new_asset.invoice_line_id.account_id.id,
                })
        elif new_asset.invoice_line_id.product_id:
            account = new_asset.invoice_line_id.get_invoice_line_account(type, new_asset.invoice_line_id.product_id, new_asset.move_id.fiscal_position_id, new_asset.move_id.company_id)
            if account:
                new_vals = {
                    'product_account_id': account.id
                }

        if new_vals:
            new_asset.write(new_vals)
        if new_asset.budget_element_id and not new_asset.is_accrued_expense:
            new_asset.calculate_element_table()

        return new_asset

    
    def validate(self):
        ret = super(AccountAssetAsset, self).validate()
        AccountMove = self.env['account.move']
        BudgetElement = self.env['budget.element']
        budget_elements = BudgetElement

        def get_carried_from_budget(element_line, year, search_budget, parent_budget):
            if not search_budget.budget_id:
                # We only search for main budgets (details and lines are searched beforehand)
                budget = BudgetElement.search([
                    ('date_start', '<=', element_line.date_end),
                    ('date_end', '>=', element_line.date_start),
                    ('carried_from_element_id', '=', search_budget.id),
                ])
                budget_type = self.env.ref('advanced_budget.budget_element_type_line')
                new_name = _('Assets {year1} to {yearN}: {budget_name}').format(year1=asset.budget_element_id.date_start[:4], yearN=year, budget_name=search_budget.name)
            else:
                budget_type = self.env.ref('advanced_budget.budget_element_type_detail')
                new_name = search_budget.name
                budget = BudgetElement

            if not budget:
                budget = BudgetElement.create({
                    'name': new_name,
                    'date_start': year + '-01-01',
                    'date_end': year + '-12-31',
                    'type_id': budget_type.id,
                    'subtype_id': self.env.ref('microcred_profile.budget_subtype_generated').id,
                    'is_readonly': True,
                    'budget_id': parent_budget.id,
                    'carried_from_element_id': search_budget.id,
                    'budget_department_id': search_budget.budget_department_id.id,
                    'all_tag_ids': [(6, 0, [x.id for x in search_budget.all_tag_ids])],
                })
                search_budget.distribution_cost_ids.copy(default={'parent_id': budget.id})
            return budget

        def get_linked_budget(asset, element_line, child_budgets_created, parents_budgets_created, year):
            element_line_found = asset.element_amortisation_ids.search([
                ('initial_element_id', '=', asset.budget_element_id.id),
                ('asset_id', '=', False),
                ('date_start', '<=', element_line.date_end),
                ('date_end', '>=', element_line.date_start),
            ], order="id desc", limit=1)
            if element_line_found and element_line_found.budget_element_id:
                child_budgets_created[year] = element_line_found.budget_element_id
                return element_line_found.budget_element_id
            if not element_line_found:
                element_line_found = asset.budget_element_id.amortisation_element_ids.create({
                    'initial_element_id': asset.budget_element_id.id,
                    'date_start': year + '-01-01',
                    'date_end': year + '-12-31'
                })
            if year in child_budgets_created:
                element_line_found.budget_element_id = child_budgets_created[year]
                return child_budgets_created[year]
            budget_id = BudgetElement.search([
                ('date_start', '<=', element_line.date_end),
                ('date_end', '>=', element_line.date_start),
                ('carried_from_element_id', '=', asset.budget_element_id.id),
            ])
            if budget_id:
                child_budgets_created[year] = budget_id
                element_line_found.budget_element_id = child_budgets_created[year]
                return budget_id
            # Need to create this element - but first, see if we can find the parent budget (if it's a detail, we'll use the main budget)
            if year in parent_budgets_created:
                new_main_budget = parent_budgets_created[year]
            else:
                main_budget = asset.budget_element_id.budget_id
                while main_budget.budget_id:
                    main_budget = main_budget.budget_id
                new_main_budget = get_carried_from_budget(element_line, year, main_budget, BudgetElement)
                parent_budgets_created[year] = new_main_budget
            new_child_budget = get_carried_from_budget(element_line, year, asset.budget_element_id, new_main_budget)
            child_budgets_created[year] = new_child_budget
            element_line_found.budget_element_id = child_budgets_created[year]
            return new_child_budget

        for asset in self:
            if asset.budget_element_id:
                budget_elements |= asset.budget_element_id

            # Renumber sequences (Odoo generates them from 0 to X - 1, but it should be from 1 to X
            cur_number = 1
            lines = asset.depreciation_line_ids.sorted(lambda r: r.sequence)  # Do this outside the loop so it doesn't get recalculated during loop iterations.
            for line in lines:
                line.sequence = cur_number
                cur_number += 1

            if asset.is_accrued_expense:
                # Create the credit note
                note_date = asset.move_id.move_id.date or asset.date
                company_currency = asset.company_id.currency_id
                current_currency = asset.currency_id
                amount = current_currency.compute(asset.value, company_currency)
                sign = (asset.journal_id.type == 'purchase' or asset.journal_id.type == 'sale' and 1) or -1
                asset_name = asset.name + ' ' + _('(credit note)')
                reference = asset.code
                journal_id = asset.journal_id.id
                partner_id = asset.partner_id.id
                categ_type = asset.type
                credit_account = asset.account_asset_id.id
                debit_account = asset.account_accrued_id.id
                tags = []
                distribution_costs = []
                if asset.account_accrued_id.authorise_analytics:
                    if asset.budget_element_id.all_tag_ids:
                        # Copy axis
                        tags = [(5, 0, 0)]
                        for tag in asset.budget_element_id.all_tag_ids:
                            tags.append((4, tag.id))
                    elif asset.invoice_line_id.all_tag_ids:
                        # Copy axis
                        tags = [(5, 0, 0)]
                        for tag in asset.invoice_line_id.all_tag_ids:
                            tags.append((4, tag.id))

                    coefficient = 1.0
                    if asset.invoice_line_id:  # Get the distribution from the invoice
                        digits_rounding_precision = asset.company_id.currency_id.rounding
                        distribution_cost_ids = asset.invoice_line_id.get_distribution_cost_ids()
                        coefficient = asset.invoice_line_id.price_subtotal and (amount / asset.invoice_line_id.price_subtotal) or 0.0
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
                                    raise UserError(_("It is impossible to allocate the amount of %f.\n\nPlease make a allocation manually") % (distribution_cost.amount_fixed))

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
                            }))

                # Accrued expense
                move_line_1 = {
                    'name': asset_name,
                    'account_id': credit_account,
                    'credit': 0.0,
                    'debit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency.id or False,
                    'amount_currency': company_currency != current_currency and - sign * amount or 0.0,
                    'analytic_account_id': asset.account_analytic_id.id if categ_type == 'sale' else False,
                    'date': note_date,
                    'budget_element_id': asset.budget_element_id.id,
                }
                move_line_2 = {
                    'name': asset_name,
                    'account_id': debit_account,
                    'debit': 0.0,
                    'credit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency.id or False,
                    'amount_currency': company_currency != current_currency and sign * amount or 0.0,
                    'analytic_account_id': asset.account_analytic_id.id if categ_type == 'purchase' else False,
                    'date': note_date,
                    'budget_element_id': asset.budget_element_id.id,
                }

                move_vals = {
                    'ref': reference + ' ' + _('Accrued expense entry'),
                    'date': note_date or False,
                    'journal_id': asset.journal_id.id,
                    'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    'asset_id': asset.id,
                }
                asset.credit_note_move_id = AccountMove.create(move_vals).id
                asset.credit_note_move_id.post()

            if not asset.element_amortisation_ids:
                # Need to create the list of element
                asset.generate_element_table()

            parent_budgets_created = {}
            child_budgets_created = {}
            for element_line in asset.element_amortisation_ids:
                year = element_line.date_start[:4]
                if not element_line.budget_element_id:
                    # Need to find the appropriate budget element
                    child_budget = get_linked_budget(asset, element_line, child_budgets_created, parent_budgets_created, year)
                    element_line.budget_element_id = child_budget.id
                    budget_elements |= child_budget

                for line in asset.depreciation_line_ids:
                    if not line.budget_element_id:
                        if line.depreciation_date[:4] == year:
                            line.budget_element_id = child_budget.id

        while budget_elements:
            for element in budget_elements:
                element.update_pl_element_amounts()
            budget_elements = budget_elements.mapped('budget_id')

        return ret

    
    def write(self, vals):
        ret = super(AccountAssetAsset, self).write(vals)
        if 'accrued_date_end' in vals or 'method_number' in vals or 'method_period' in vals:
            asset_table = self.generate_element_table()
            if asset_table:
                new_table = []
                for table_line in asset_table:
                    new_table.append(table_line[2])

                new_lines = []
                found_lines = []
                for old_line in self.element_amortisation_ids:
                    found = False
                    for table_line in new_table:
                        if table_line['date_start'] == old_line.date_start:
                            new_lines.append((1, old_line.id, {
                                'amount_amortised': table_line['amount_amortised'],
                            }))
                            found_lines.append(table_line['date_start'])
                            found = True
                            break

                    if not found:
                        new_lines.append((2, old_line.id))

                for table_line in new_table:
                    if table_line['date_start'] not in found_lines:
                        new_lines.append((0, 0, table_line))
                super(AccountAssetAsset, self).write({
                    'element_amortisation_ids': new_lines
                })

        if 'element_amortisation_ids' in vals:
            for asset in self:
                for line in asset.depreciation_line_ids:
                    if not line.move_check or True:
                        for budget_line in asset.element_amortisation_ids:
                            if line.depreciation_date >= budget_line.date_start and line.depreciation_date <= budget_line.date_end:
                                line.budget_element_id = budget_line.budget_element_id.id
                                break

        return ret

    
    def compute_depreciation_board(self):
        self.ensure_one()
        if self.prorata and self.daily_prorata:
            if not self.env.context.get('date_sold'):
                posted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
                posted_periods = {}
                period_amounts = defaultdict(float)
                for line in posted_depreciation_line_ids:
                    period = line.depreciation_date[:7]
                    posted_periods[period] = line
                    period_amounts[period] = line.amount

                # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
                unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: not x.move_check)
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

                date_start = datetime.strptime(self.date, DF)
                date_end = self.accrued_date_end and datetime.strptime(self.accrued_date_end, DF) or date_start + relativedelta(months=self.method_number, days=-1)

                # Get the number of days (ignoring periods that have already been posted)
                date_cur = date_start
                number_of_days = 0
                days_per_period = defaultdict(int)
                while date_cur <= date_end:
                    period = date_cur.strftime('%Y-%m')
                    if period not in posted_periods:
                        number_of_days += 1
                        days_per_period[period] += 1
                    date_cur += relativedelta(days=1)

                # Calculate the amount per period
                period_amounts = defaultdict(float)
                total_amount = 0.0
                for period in sorted(days_per_period.keys()):
                    this_amount = self.currency_id.round((self.value_residual * days_per_period[period]) / number_of_days)
                    period_amounts[period] = this_amount
                    total_amount += this_amount

                # Apply the rounding error to the first "new" period
                delta = 0.0
                if total_amount != self.value_residual:
                    delta = self.value_residual - total_amount

                current_value = self.value
                cumulative_amount = 0.0
                sequence = 0
                for period in sorted(period_amounts.keys()):
                    cumulative_amount += period_amounts[period]
                    if period in posted_periods.keys():
                        # It's a posted period - change the remaining value
                        posted_periods[period].remaining_value = current_value
                    else:
                        # It's a new period - create the values
                        period_amounts[period] += delta
                        cumulative_amount += delta
                        delta = 0.0
                        period_date = period + '-01'
                        if self.end_of_month:
                            period_date = (datetime.strptime(period_date, DF) + relativedelta(months=1, days=-1)).strftime(DF)
                        elif period_date < self.date:
                            period_date = self.date

                        budget_element_id = False
                        for budget_line in self.element_amortisation_ids:
                            if period_date >= budget_line.date_start and period_date <= budget_line.date_end:
                                budget_element_id = budget_line.budget_element_id.id
                                break

                        vals = {
                            'amount': period_amounts[period],
                            'asset_id': self.id,
                            'sequence': sequence,
                            'name': (self.code or '') + '/' + str(sequence),
                            'remaining_value': self.value - cumulative_amount,
                            'depreciated_value': cumulative_amount,
                            'depreciation_date': period_date,
                            'budget_element_id': budget_element_id,
                        }

                    current_value -= period_amounts[period]
                    sequence += 1
                    commands.append((0, False, vals))

                self.write({'depreciation_line_ids': commands})
        else:
            ret = super(AccountAssetAsset, self).compute_depreciation_board()
            unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: not x.move_check)
            for line in unposted_depreciation_line_ids:
                line_write = {}
                if self.end_of_month:
                    line_write['depreciation_date'] = (datetime.strptime(line.depreciation_date, DF) + relativedelta(day=1) + relativedelta(months=1, days=-1)).strftime(DF)

                budget_element_id = False
                for budget_line in self.element_amortisation_ids:
                    if line.depreciation_date >= budget_line.date_start and line.depreciation_date <= budget_line.date_end:
                        budget_element_id = budget_line.budget_element_id.id
                        break

                line_write['budget_element_id'] = budget_element_id
                line.write(line_write)

            return ret

    
    def generate_element_table(self):
        self.ensure_one()
        new_table = {}
        if self.budget_element_id:
            table_amounts = defaultdict(float)
            for line in self.depreciation_line_ids:
                if line.depreciation_date <= self.budget_element_id.date_end:
                    table_amounts[self.budget_element_id.date_end] += line.amount
                else:
                    end_date = line.depreciation_date[:4] + '-12-31'
                    table_amounts[end_date] += line.amount

            new_table = []
            for date_end in table_amounts:
                budget_element_id = False
                if date_end == self.budget_element_id.date_end:
                    date_start = self.budget_element_id.date_start
                    if not date_start:
                        budget = self.budget_element_id
                        while budget and not budget.date_start:
                            budget = budget.budget_id

                        if budget:
                            date_start = budget.start_date

                    budget_element_id = self.budget_element_id.id
                else:
                    date_start = date_end[:4] + '-01-01'
                    if date_start < self.budget_element_id.date_end:
                        date_start = (datetime.strptime(self.budget_element_id.date_end, '%Y-%m-%d') + relativedelta(days=-1)).strftime('%Y-%m-%d')

                new_table.append((0, 0, {
                    'date_start': date_start,
                    'date_end': date_end,
                    'budget_element_id': budget_element_id,
                    'initial_element_id': self.budget_element_id.id,
                    'amount_amortised': table_amounts[date_end],
                    'can_modify': (budget_element_id is not False)
                }))

        return new_table

    
    def calculate_element_table(self):
        for asset in self:
            new_table = asset.generate_element_table()
            if new_table:
                self.element_amortisation_ids.unlink()
                asset.write({
                    'element_amortisation_ids': new_table
                })


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
