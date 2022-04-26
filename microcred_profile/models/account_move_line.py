# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Yannis Pou-Vich <yannis.pouvich@syleam.fr>
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

from odoo import fields, models, api, _
from odoo.tools import float_round, float_is_zero
from collections import defaultdict
import odoo.addons.decimal_precision as dp


class AccountMoveLine(models.Model):
    _inherit = ['account.move.line', 'account.axis.tag.wrapper']
    _name ="account.move.line"

    tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string='move line Tags', help='tag')
    export_id = fields.Many2one('account.journal.sage.export', string='Sage export')
    budget_element_id = fields.Many2one('budget.element', string='Budget element', help='The budget element linked to this account move line.')
    distribution_partner_ids = fields.One2many('account.move.line.distribution', 'move_line_id', string='Partner distribution')
    reinvoice_batch_ids = fields.Many2many('budget.reinvoice.batch', string='Reinvoiced batches', help='The reinvoicing batches referring to this move line.',
                                           compute='_get_reinvoice_batches', )
    can_redistribute = fields.Boolean(string='Can redistribute', compute='_get_reinvoice_batches', )
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line', help='The invoice line linked to this account move (if any).')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', help='The employee for the line.')  # Used on payroll imports
    invoice_state = fields.Selection(selection=[('na', 'N/A'), ('paid', 'Paid'), ('not_paid', 'Not paid')], string='Invoice state',
                                     help='The status of the invoice linked to this journal item.', compute='_get_invoice_state')
    authorise_analytics = fields.Boolean(string='Authorise Analytics', related='account_id.authorise_analytics', readonly=True,
                                         help='If checked, the analytical data will be implemented for journal items using this account.')
    reinvoiced_amount = fields.Float(string='Reinvoiced amount', digits=("Account"), help='The amount this invoice has been reinvoiced.')
    text_distribution = fields.Char(string='Specific distribution', size=128, help='The specific distribution.', store=True, compute='_get_text_distribution', )

    
    def _get_invoice_state(self):
        for move_line in self:
            if not move_line.move_id:
                move_line.invoice_state = 'na'
            elif move_line.move_id.state == 'paid':
                move_line.invoice_state = 'paid'
            else:
                move_line.invoice_state = 'not_paid'

    
    def _get_reinvoice_batches(self):
        for move_line in self:
            move_line.update({
                'reinvoice_batch_ids': move_line.mapped('distribution_partner_ids.reinvoice_batch_id.id'),
                'can_redistribute': (len(move_line.reinvoice_batch_ids) == 0)
            })

    
    def write(self, values):
        """
        If the budget element is updated, update the invoice line as well
        """
        recalc_budgets = self.env['budget.element']

        ret = super(AccountMoveLine, self).write(values)
        if 'budget_element_id' in values:
            # Since we're manually handling budget calculation, we need to recalculate old budgets
            recalc_budgets |= self.filtered(lambda r: r.budget_element_id is not False).mapped('budget_element_id')
            if 'tag_ids' not in values:
                # Copy the budget element's tags
                analytical_lines = self.filtered(lambda r: r.authorise_analytics is True)
                if analytical_lines:
                    # Note : Since the budget element has been updated, all the journal items have the same budget element, so we can read only the first journal item's budget element
                    super(AccountMoveLine, analytical_lines).write({'all_tag_ids': [(6, 0, [tag.id for tag in analytical_lines[0].budget_element_id.all_tag_ids])]})
        
        if 'all_tag_ids' in values or 'distribution_partner_ids' in values:
            bad_lines = self.filtered(lambda r: r.authorise_analytics is False)
            if bad_lines:
                super(AccountMoveLine, bad_lines).write({
                    'tag_ids': [(5, 0, 0)],
                    'distribution_partner_ids': [(5, 0, 0)]
                })

        if ('budget_element_id' in values or
                'debit' in values or
                'credit' in values) and 'distribution_partner_ids' not in values:
            # We need to copy the distributions for each journal item
            for line in self:
                if line.account_id.authorise_analytics:
                    new_distributions = [(5, 0, 0)]
                    if line.budget_element_id:
                        main_budget = line.budget_element_id
                        while main_budget and not main_budget.distribution_cost_ids:
                            main_budget = main_budget.budget_id

                        distribution_amounts = defaultdict(float)
                        amount = line.credit or line.debit
                        remaining = amount
                        max_distribution_partner = False
                        max_distribution_amount = 0.0
                        for distribution in main_budget.distribution_cost_ids:
                            line_amount = float_round((amount * distribution.equivalent_percentage) / 100.0, precision_digits=2)
                            partner = distribution.child_id.id
                            remaining -= line_amount
                            distribution_amounts[partner] += line_amount
                            if distribution_amounts[partner] > max_distribution_amount:
                                max_distribution_partner = partner
                                max_distribution_amount = distribution_amounts[partner]

                        if not float_is_zero(remaining, precision_digits=2) and max_distribution_partner:
                            distribution_amounts[max_distribution_partner] += remaining

                        for distribution in distribution_amounts:
                            new_distributions.append(
                                (0, 0, {
                                    'budget_partner_id': distribution,
                                    'amount_fixed': distribution_amounts[distribution]
                                }))
                    line.write({
                        'distribution_partner_ids': new_distributions,
                    })

        # if 'budget_element_id' in values and not self._context.get('no_budget_element_transfer'):
        #     self.mapped('invoice_line_id').write({'budget_element_id': values['budget_element_id']})

        # if 'all_tag_ids' in values:
        #     self.set_axis_fields()

        if 'budget_element_id' in values or \
           'credit' in values or \
           'debit' in values:
            recalc_budgets |= self.filtered(lambda r: r.budget_element_id is not False).mapped('budget_element_id')

        if recalc_budgets and not self.env.context.get('do_not_calculate_budgets', False):
            recalc_budgets.calculate_amounts()

        return ret

#     @api.model
#     def create(self, values):
#         """
#         Recalculate the amounts of budgets
#         """
#         account = False
#         # if values.get('tag_ids') or values.get('distribution_partner_ids'):
#         #     # Check that we can accept them
#         #     account = self.account_id.browse(values['account_id'])
#         #     if not account.authorise_analytics:
#         #         values.pop('tag_ids', False)
#         #         values.pop('distribution_partner_ids', False)

#         if values.get('budget_element_id', False):
#             budget_element = self.budget_element_id.browse(values['budget_element_id'])
#             if not account:
#                 account = self.account_id.browse(values['account_id'])

#             # if account.authorise_analytics and 'all_tag_ids' not in values:
#             #     # Copy the budget element's tags
#             #     values['all_tag_ids'] = [(6, 0, [tag.id for tag in budget_element.all_tag_ids])]

#             if not values.get('product_id'):
#                 values['product_id'] = budget_element.company_id.default_expensify_product_id.id

#             if 'distribution_partner_ids' not in values:
#                 # Copy the budget element's distribution
#                 main_budget = budget_element
#                 while main_budget and not main_budget.distribution_cost_ids:
#                     main_budget = main_budget.budget_id

#                 if main_budget:
#                     distribution_amounts = defaultdict(float)
#                     amount = values.get('credit', 0) + values.get('debit', 0)
#                     remaining = amount
#                     max_distribution_partner = False
#                     max_distribution_amount = 0.0
#                     for distribution in main_budget.distribution_cost_ids:
#                         line_amount = float_round((amount * distribution.equivalent_percentage) / 100.0, precision_digits=2)
#                         partner = distribution.child_id.id
#                         remaining -= line_amount
#                         distribution_amounts[partner] += line_amount
#                         if distribution_amounts[partner] > max_distribution_amount:
#                             max_distribution_partner = partner
#                             max_distribution_amount = distribution_amounts[partner]

#                     if not float_is_zero(remaining, precision_digits=2) and max_distribution_partner:
#                         distribution_amounts[max_distribution_partner] += remaining

#                     new_distributions = []
#                     for distribution in distribution_amounts:
#                         new_distributions.append(
#                             (0, 0, {
#                                 'budget_partner_id': distribution,
#                                 'amount_fixed': distribution_amounts[distribution]
#                             }))
#                     values['distribution_partner_ids'] = new_distributions

#         # Swap accounts (used with assets)
#         if self._context.get('swap_account'):
#             if values.get('account_id') == self._context['swap_account'][0]:
#                 values['account_id'] = self._context['swap_account'][1]

#         if self._context.get('swap_accounts'):
#             for swap in self._context.get('swap_accounts'):
#                 if values.get('account_id') == swap[0]:
#                     values['account_id'] = swap[1]
#                     break

#         ret = super(AccountMoveLine, self).create(values)
#         if self.env.context.get('statement_line'):
#             statement_line = self.env.context['statement_line']
#             if ret.account_id.authorise_analytics and statement_line.budget_element_id:
#                 new_distributions = [(5, 0, 0)]
#                 distribution_amounts = defaultdict(float)
#                 amount = ret.credit or ret.debit or 0.0
#                 remaining = amount
#                 max_distribution_partner = False
#                 max_distribution_amount = 0.0
#                 for distribution in statement_line.budget_element_id.distribution_cost_ids:
#                     line_amount = float_round((amount * distribution.equivalent_percentage) / 100.0, precision_digits=2)
#                     partner = distribution.child_id.id
#                     remaining -= line_amount
#                     distribution_amounts[partner] += line_amount
#                     if distribution_amounts[partner] > max_distribution_amount:
#                         max_distribution_partner = partner
#                         max_distribution_amount = distribution_amounts[partner]

#                 if not float_is_zero(remaining, precision_digits=2) and max_distribution_partner:
#                     distribution_amounts[max_distribution_partner] += remaining

#                 for distribution in distribution_amounts:
#                     new_distributions.append(
#                         (0, 0, {
#                             'budget_partner_id': distribution,
#                             'amount_fixed': distribution_amounts[distribution]
#                         }))

#                 ret.update({
#                     'budget_element_id': statement_line.budget_element_id.id,
#                     # 'all_tag_ids': [(6, 0, [x.id for x in statement_line.all_tag_ids])],
#                     'distribution_partner_ids': new_distributions,
#                 })

#         if ret.budget_element_id and not self.env.context.get('do_not_calculate_budgets', False):
#             ret.budget_element_id.calculate_amounts()

#         return ret

    
    def unlink(self):
        """
        Recalculate budgets from deleted lines
        """
        recalc_budgets = self.filtered(lambda r: r.budget_element_id is not False).mapped('budget_element_id')
        ret = super(AccountMoveLine, self).unlink()
        recalc_budgets.calculate_amounts()
        return ret

    @api.onchange('budget_element_id')
    def onchange_budget_element(self):
        """
        Copy the budget element's tags
        """

        # self.ensure_one()
        # if self.budget_element_id.all_tag_ids and self.authorise_analytics:
        #     # Copy axis
        #     self.update({
        #         'all_tag_ids': [(6, 0, [tag.id for tag in self.budget_element_id.all_tag_ids])]
        #     })
        # if not self.product_id:
        #     self.update({
        #         'product_id': self.company_id.default_expensify_product_id.id
        #     })

    
    def calculate_reinvoiced_amount(self):
        for move_line in self:
            amount = 0.0
            for line in move_line.distribution_partner_ids:
                if line.reinvoice_batch_id:
                    amount += line.amount_fixed
            move_line.reinvoiced_amount = amount

    @api.depends(
        'distribution_partner_ids',
    )
    def _get_text_distribution(self):
        """
        Calculate the text containing the distribution (if specific).
        """
        for line in self:
            distributions = defaultdict(float)
            text_distributions = []
            total = 0.0
            for distribution in line.distribution_partner_ids:
                distributions[distribution.budget_partner_id] += distribution.amount_fixed
                total += distribution.amount_fixed

            for distribution in distributions:
                text_distributions.append(_('%s: %.2f%% (%.2f)') % (distribution.name,
                    float_round((distributions[distribution] * 100.0) / (total or 0.1), precision_digits=2),
                    float_round(distributions[distribution], precision_digits=2)))

            if distributions:
                line.text_distribution = ', '.join(text_distributions)
            else:
                line.text_distribution = _("None")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
