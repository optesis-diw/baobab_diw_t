# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.syleam.fr/>)
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
from odoo.tools import float_is_zero, float_round
from collections import defaultdict


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    budget_element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='Select the budget element.')
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags3', readonly=True,
                                   help='This contains the axis tags for this bank statement line.')
    distribution_cost_ids = fields.One2many('budget.element.distribution', 'statement_line_id', string='Cost distribution')
    text_distribution = fields.Char(string='Distribution', size=128, help='The distribution.', compute='_get_text_distribution', )

    @api.onchange('budget_element_id')
    def onchange_element(self):
        for element in self:
            if element.budget_element_id:
                element.all_tag_ids = [(6, 0, [x.id for x in element.budget_element_id.all_tag_ids])]

    
    def _get_text_distribution(self):
        """
        Calculate the text containing the distribution (if specific).
        """
        for line in self:
            distributions = []
            for distribution in line.distribution_cost_ids:
                if distribution.amount_fixed:
                    distributions.append(_('%s: %.2f') % (distribution.child_id.name, distribution.amount_fixed))
                else:
                    distributions.append(_('%s: %.2f%% (%.2f)') % (distribution.child_id.name, distribution.percentage, distribution.amount_fixed or (line.amount * distribution.percentage) / 100.0))

            if distributions:
                line.text_distribution = ', '.join(distributions)
            else:
                line.text_distribution = _("None")

    
    def copy_budget_distribution(self):
        self.mapped('distribution_cost_ids').unlink()
        for line in self:
            # Get best costs
            element = line.budget_element_id
            while not element.distribution_cost_ids and element:
                element = element.budget_id

            if element:
                for cost in element.distribution_cost_ids:
                    cost.copy(default={
                        'statement_line_id': line.id,
                        'parent_id': False,
                    })

    
    def write(self, vals):
        ret = super(AccountBankStatementLine, self).write(vals)
        if 'budget_element_id' in vals:
            self.copy_budget_distribution()
            new_vals = {
                'all_tag_ids': [(6, 0, [x.id for x in self.budget_element_id.all_tag_ids])]
            }
            super(AccountBankStatementLine, self).write(new_vals)
        return ret

    @api.model
    def create(self, vals):
        new_line = super(AccountBankStatementLine, self).create(vals)
        if 'budget_element_id' in vals:
            new_line.copy_budget_distribution()
            new_line.all_tag_ids = [(6, 0, [x.id for x in new_line.budget_element_id.all_tag_ids])]
        return new_line

    
    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        ret = super(AccountBankStatementLine, self.with_context({'statement_line': self})).process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec, new_aml_dicts=new_aml_dicts)
        if self.statement_id.journal_type == 'cash':
            ret.post()
            if self.statement_id.all_lines_reconciled and self.statement_id.currency_id.is_zero(self.statement_id.difference):
                self.statement_id.button_confirm_bank()

        return ret

    
    def _prepare_reconciliation_move_line(self, move, amount):
        ret = super(AccountBankStatementLine, self)._prepare_reconciliation_move_line(move, amount)
        account = self.env['account.account'].browse(ret['account_id'])
        if account.authorise_analytics and self.budget_element_id:
            new_distributions = [(5, 0, 0)]
            if self.budget_element_id:
                distribution_amounts = defaultdict(float)
                amount = abs(self.amount)
                remaining = amount
                max_distribution_partner = False
                max_distribution_amount = 0.0
                for distribution in self.budget_element_id.distribution_cost_ids:
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
            ret.update({
                'budget_element_id': self.budget_element_id.id,
                'all_tag_ids': [(6, 0, [x.id for x in self.all_tag_ids])],
                'distribution_partner_ids': new_distributions,
            })
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
