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

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class WizardAddBudgetDistributionLine(models.TransientModel):
    _inherit = "wizard.add.budget.distribution.line"

    percentage = fields.Float(digits=(7, 3))
    allow_fixed_and_percent = fields.Boolean(string='Allow percentage and fixed')
    value_changed = fields.Boolean(string='Value changed')

    
    def _check_individual_percentage_and_fixed(self):
        if self.amount_fixed and self.percentage and not self.allow_fixed_and_percent:
            return False
        return True

    @api.onchange('amount_fixed')
    def onchange_fixed(self):
        if not self.value_changed and self.allow_fixed_and_percent:
            self.value_changed = True
            self.percentage = self.wizard_id.amount and (self.amount_fixed * 100.0) / self.wizard_id.amount or 0.0
            self.value_changed = False

    @api.onchange('percentage')
    def onchange_percentage(self):
        if not self.value_changed and self.allow_fixed_and_percent:
            self.value_changed = True
            self.amount_fixed = (self.wizard_id.amount * self.percentage) / 100.0
            self.value_changed = False


class WizardAddBudgetDistribution(models.TransientModel):
    _inherit = "wizard.add.budget.distribution"

    move_line_id = fields.Many2one('account.move.line', string='Move line', readonly=True, )
    asset_line_id = fields.Many2one('account.asset', string='Asset')
    statement_line_id = fields.Many2one(comodel_name='account.bank.statement.line', string='Statement line')
    is_locked = fields.Boolean(string='Is locked')
    not_unique = fields.Boolean(string='Not unique')
    allow_fixed_and_percent = fields.Boolean(string='Allow percentage and fixed')

    
    def create_new_lines(self, model):
        new_lines = [(5, 0, 0)]
        for distribution in model.distribution_cost_ids:
            new_lines.append(
                [0, 0, {
                    'child_id': distribution.child_id.id,
                    'amount_fixed': float_round(distribution.amount_fixed or (self.allow_fixed_and_percent and distribution.percentage * self.amount / 100.0), precision_digits=2),
                    'percentage': distribution.percentage,
                    'amount_calculated': float_round(distribution.amount_fixed or (self.allow_fixed_and_percent and distribution.percentage * self.amount / 100.0), precision_digits=2),
                    'allow_fixed_and_percent': self.allow_fixed_and_percent
                }]
            )

        return new_lines

    @api.model
    def default_get(self, fields_list):
        """
        Return budget line information
        """

        values = super(WizardAddBudgetDistribution, self).default_get(fields_list)
        move_line = False
        distributions = []
        generic_id = False

        if self.env.context.get('active_model') == 'account.move.line':
            # Add the appropriate account_move_line (if any) and lock if customer invoice(s) are validated
            invoice_line = self.env['account.move.line'].browse(values['invoice_line_id'])
            if invoice_line.move_id.id:  # We are expecting some account moves
                account_moves = self.env['account.move.line'].search([('invoice_line_id', '=', invoice_line.id)])
                if len(account_moves) != 1:  # We need to find the right one by alternate methods
                    account_moves = self.env['account.move.line'].search([
                        ('move_id', '=', invoice_line.move_id.id),
                        ('product_id', '=', invoice_line.product_id.id),
                        ('quantity', '=', invoice_line.quantity)
                    ])
                if len(account_moves) == 0:  # Found none - try without the quantity
                    account_moves = self.env['account.move.line'].search([
                        ('move_id', '=', invoice_line.move_id.id),
                        ('product_id', '=', invoice_line.product_id.id),
                    ])
                if len(account_moves) == 1:
                    values['move_line_id'] = account_moves.id
                    move_line = account_moves
                else:
                    values['not_unique'] = True

        elif self.env.context.get('active_model') == 'account.bank.statement.line':
            generic_id = self.env.context.get('active_id')
            values['statement_line_id'] = generic_id
            values['amount'] = self.env['account.bank.statement.line'].browse(generic_id).amount

        elif self.env.context.get('active_model') == 'account.move.line':
            element_id = self.env.context.get('active_id')
            values['move_line_id'] = element_id
            move_line = self.env['account.move.line'].browse(element_id)

        elif self.env.context.get('active_model') == 'account.asset':
            element_id = self.env.context.get('active_id')
            values['asset_line_id'] = element_id
            asset_line = self.env['account.asset'].browse(element_id)
            values['amount'] = asset_line.amount
            values['allow_fixed_and_percent'] = True
            if asset_line.distribution_cost_ids:
                for distribution in asset_line.distribution_cost_ids:
                    distributions.append(
                        [0, 0, {
                            'child_id': distribution.child_id.id,
                            'amount_fixed': distribution.amount_fixed,
                            'percentage': (100 * distribution.amount_fixed) / ((distribution.asset_line_id.amount) or 0.001),
                            'amount_calculated': distribution.amount_fixed,
                            'allow_fixed_and_percent': True,
                        }]
                    )
            elif asset_line.asset_id.invoice_line_id:  # Get the data from the invoice line instead
                for distribution in asset_line.asset_id.invoice_line_id.distribution_cost_ids:
                    amount = (distribution.amount_fixed or distribution.amount_calculated)
                    coeff = asset_line.asset_id.invoice_line_id.price_subtotal and amount / asset_line.asset_id.invoice_line_id.price_subtotal or 0.0
                    distributions.append(
                        [0, 0, {
                            'child_id': distribution.child_id.id,
                            'amount_fixed': asset_line.amount * coeff,
                            'percentage': (100 * amount) / ((asset_line.asset_id.invoice_line_id.price_subtotal) or 0.001),
                            'amount_calculated': asset_line.amount * coeff,
                            'allow_fixed_and_percent': True,
                        }]
                    )

        if generic_id:
            # This is used to load any generic distribution costs
            for distribution in self.env[self.env.context['active_model']].browse(generic_id).distribution_cost_ids:
                distributions.append(
                    [0, 0, {
                        'child_id': distribution.child_id.id,
                        'amount_fixed': distribution.amount_fixed,
                        'percentage': distribution.percentage,
                        'amount_calculated': (values.get('amount', 0.0) * distribution.percentage) / 100.0,
                    }]
                )

        if move_line:  # This is priority with respect to invoice line
            values['allow_fixed_and_percent'] = True
            values['amount'] = move_line.credit + move_line.debit
            distributions = []
            if move_line.reinvoice_batch_ids:  # We need to see if the corresponding partner invoice has been validated or not
                for distribution in move_line.distribution_partner_ids:
                    if distribution.reinvoice_invoice_line_id.move_id and distribution.reinvoice_invoice_line_id.move_id.state != 'draft':
                        values['is_locked'] = True
                        break
            for distribution in move_line.distribution_partner_ids:
                distributions.append(
                    [0, 0, {
                        'child_id': distribution.budget_partner_id.id,
                        'amount_fixed': distribution.amount_fixed,
                        'percentage': (100 * distribution.amount_fixed) / (move_line.credit + move_line.debit),
                        'amount_calculated': distribution.amount_fixed,
                        'allow_fixed_and_percent': True,
                    }]
                )
            if not distributions and 'line_ids' in values:
                # Allow percentage and fixed
                for old_distri in values['line_ids']:
                    old_distri[2]['allow_fixed_and_percent'] = True
                    distributions.append(old_distri)

        if distributions:
            values['line_ids'] = distributions

        return values

    
    def validate(self):
        """
        Validate the details
        """
        for wizard in self:
            if wizard.move_line_id:
                wizard.move_line_id.distribution_partner_ids.unlink()
                new_distributions = []
                total = 0.0
                for distribution in wizard.line_ids:
                    distribution.percentage = False
                    if not distribution.amount_fixed:
                        distribution.amount_calculated = (distribution.percentage * wizard.amount) / 100

                    new_distributions.append(
                        (0, 0, {
                            'move_line_id': wizard.move_line_id.id,
                            'budget_partner_id': distribution.child_id.id,
                            'amount_fixed': distribution.amount_calculated,
                        }))
                    total += distribution.amount_calculated

                if float_compare(total, wizard.amount, precision_rounding=2):
                    raise UserError(_('The total (%.2f) of the individual lines must be equal to that of the move line (%.2f).') % (total, wizard.amount))

                if new_distributions:
                    wizard.move_line_id.write({'distribution_partner_ids': new_distributions})
                if wizard.invoice_line_id:  # We also have a linked invoice line
                    return super(WizardAddBudgetDistribution, self).validate()

            elif wizard.asset_line_id:
                wizard.asset_line_id.distribution_cost_ids.unlink()
                new_distributions = []
                total = 0.0
                for distribution in wizard.line_ids:
                    if not distribution.amount_fixed:
                        distribution.amount_calculated = (distribution.percentage * wizard.amount) / 100

                    new_distributions.append(
                        (0, 0, {
                            'asset_line_id': wizard.asset_line_id.id,
                            'child_id': distribution.child_id.id,
                            'amount_fixed': distribution.amount_calculated,
                        }))
                    total += distribution.amount_calculated

                if float_compare(total, wizard.amount, precision_rounding=2):
                    raise UserError(_('The total (%.2f) of the individual lines must be equal to that of the move line (%.2f).') % (total, wizard.amount))

                if new_distributions:
                    wizard.asset_line_id.write({'distribution_cost_ids': new_distributions})

            else:
                this_element = False
                if wizard.statement_line_id:
                    this_element = (wizard.statement_line_id, 'statement_line_id')
                return super(WizardAddBudgetDistribution, wizard).validate(this_element=this_element)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
