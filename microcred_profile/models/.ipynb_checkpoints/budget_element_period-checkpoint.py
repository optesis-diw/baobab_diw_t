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
from odoo.tools import float_round, float_compare
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import logging
logger = logging.getLogger('microcred_profile')


class BudgetElementPeriod(models.Model):
    _name = 'budget.element.period'
    _description = 'Budget element period'
    _order = 'id desc'

    budget_element_id = fields.Many2one('budget.element', string='Budget element', help='The budget element.', index=True)
    period_id = fields.Many2one('account.period', string='Period', help='The period.', index=True, readonly=True)
    amount_fixed = fields.Float(string='Fixed amount', digits=("Account"), help='Enter the fixed amount.')
    amount_initial = fields.Float(string='Initial amount', digits=("Account"), help='The initial amount.', readonly=True)
    amount_current = fields.Float(string='Current amount', digits=("Account"), help='The current amount.')
    amount_engaged = fields.Float(string='Engaged amount', digits=("Account"), help='The engaged amount.', readonly=True)
    amount_invoiced = fields.Float(string='Invoiced amount', digits=("Account"), help='The invoiced amount.', readonly=True)
    amount_calculated = fields.Float(string='Calculated amount', digits=("Account"), readonly=True)
    amount_remaining = fields.Float(string='Remaining amount', digits=("Account"), readonly=True)
    has_manual_change = fields.Boolean(string='Manual change', help='Has been manually changed.')

    profit_loss_amount_fixed = fields.Float(string='P&L Fixed amount', digits=("Account"), help='The P&L fixed amount.', readonly=True)
    profit_loss_amount_initial = fields.Float(string='P&L Initial amount', digits=("Account"), help='The P&L initial amount.', readonly=True)
    profit_loss_amount_engaged = fields.Float(string='P&L Engaged amount', digits=("Account"), help='The P&L engaged amount.', readonly=True)
    profit_loss_amount_invoiced = fields.Float(string='P&L Invoiced amount', digits=("Account"), help='The P&L invoiced amount.', readonly=True)
    profit_loss_amount_remaining = fields.Float(string='P&L Remaining amount', digits=("Account"), help='The P&L amount remaining.', readonly=True)

    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency', related='budget_element_id.company_id.currency_id', readonly=True)
    last_error_date = fields.Date(string='Last error date', help='The last date an error was detected.')
    linked_period_id = fields.Many2one(comodel_name='budget.element.period', string='Linked period', help='The linked period element', compute='_compute_linked_period')

    
    def _compute_linked_period(self):
        for period in self:
            linked_period = False
            if period.budget_element_id.linked_distribution_id:
                linked_period = self.search([
                    ('budget_element_id', '=', period.budget_element_id.linked_distribution_id.parent_id.id),
                    ('period_id', '=', period.period_id.id),
                ]).id

            period.linked_period_id = linked_period

    
    def calculate_planned(self):
        for period in self:
            if period.budget_element_id.is_readonly:  # We only do this to calculated elements
                amount = 0.0
                periods = self.search([
                    ('budget_element_id', '=', period.budget_element_id.linked_distribution_id.parent_id.id),
                    ('period_id', '=', period.period_id.id),
                ])
                for subperiod in periods:
                    amount += subperiod.amount_fixed
                period.amount_fixed = amount

    
    def _get_engaged_amount(self):
        """
        Calculate the engaged amount
        """
        for period in self:
            amount = 0.0
            element = period.budget_element_id
            if element.type in ('budget_line', 'budget_detail'):
                if not element.linked_distribution_id:
                    # Calculate from purchase order lines
                    all_element_ids = [element.id]
                    all_element_ids.extend(element.mapped('budget_detail_ids.id'))
                    purchase_lines = self.env['purchase.order.line'].sudo().search([
                        ('budget_element_id', 'in', all_element_ids),
                        ('order_id.state', 'not in', ('draft', 'sent', 'cancel')),
                        ('order_id.date_order', '>=', period.period_id.date_start),
                        ('order_id.date_order', '<=', period.period_id.date_end),
                    ])
                    for line in purchase_lines:
                        amount += line.price_subtotal
                elif period.linked_period_id:
                    amount = (period.linked_period_id.amount_engaged * element.linked_distribution_id.percentage) / 100.0

            else:
                # Calculate from budget lines (sub-budgets are included as budget lines)
                # Budget lines
                for line in element.budget_line_ids:
                    amount += line.amount_engaged

            period.amount_engaged = amount

    
    def set_invoiced_amount(self):
        """
        Calculate the invoiced amount - note this must be done from bottom to top in order to work
        """
        for period in self:
            amount = 0.0
            element = period.budget_element_id

            if element.linked_distribution_id and period.linked_period_id:
                amount += (period.linked_period_id.amount_invoiced * element.linked_distribution_id.percentage) / 100.0
            else:
                # All account move lines
                account_lines = self.env['account.move.line'].sudo().search([
                    ('budget_element_id', '=', element.id),
                    ('date', '>=', period.period_id.date_start),
                    ('date', '<=', period.period_id.date_end),
                ])
                for line in account_lines:
                    amount += (line.debit - line.credit)

                # Add any read-only amounts
                child_elements = False
                if element.type in ('periodic', 'project'):
                    child_elements = element.mapped('budget_line_ids')
                elif element.type == 'budget_line':
                    child_elements = element.mapped('budget_detail_ids')
                if child_elements:  # We have child elements - get their invoiced amounts
                    child_periods = self.search([
                        ('budget_element_id', 'in', child_elements.ids),
                        ('period_id', '=', period.period_id.id),
                    ])
                    for child_period in child_periods:
                        amount += child_period.amount_invoiced

            period.amount_invoiced = amount

    
    def _get_remaining_amount(self):
        """
        Calculate the remaining amount
        """
        for period in self:
            amount = period.amount_invoiced
            element = period.budget_element_id
            if element.type in ('budget_line', 'budget_detail'):
                if not element.linked_distribution_id:
                    # Calculate from purchase order lines
                    all_element_ids = [element.id]
                    all_element_ids.extend(element.mapped('budget_detail_ids.id'))
                    purchase_lines = self.env['purchase.order.line'].sudo().search([
                        ('budget_element_id', 'in', all_element_ids),
                        ('order_id.state', 'not in', ('draft', 'sent', 'cancel')),
                        ('order_id.date_order', '>=', period.period_id.date_start),
                        ('order_id.date_order', '<=', period.period_id.date_end),
                        ('invoice_lines', '=', False),
                    ])
                    for line in purchase_lines:
                        amount += line.price_subtotal

                else:
                    amount = element.linked_distribution_id.amount_engaged

            period.amount_remaining = element.amount_fixed - amount

    @api.model
    def update_initial(self, vals):
        self.ensure_one()
        write_period = {}
        if self.budget_element_id.state == 'draft':
            if 'amount_fixed' in vals:
                write_period['amount_initial'] = vals['amount_fixed']

            if 'profit_loss_amount_fixed' in vals:
                write_period['profit_loss_amount_initial'] = vals['profit_loss_amount_fixed']

        if write_period:
            self.write(write_period)

    @api.model
    def create(self, vals):
        """
        Set the initial amount if the budget is in draft
        """
        period = super(BudgetElementPeriod, self).create(vals)
        period.update_initial(vals)

        return period

    
    def write(self, vals):
        """
        Set the initial amount if the budget is in draft
        """
        ret = super(BudgetElementPeriod, self).write(vals)

        if 'amount_fixed' in vals or 'profit_loss_amount_fixed' in vals:
            for period in self:
                period.update_initial(vals)

        return ret

    
    def update_if_different(self, fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                            pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts):
        def y_m_calc(date):
            return date

        def get_period_list(original_list, one_period=False):
            new_list = original_list
            if one_period:
                new_list = new_list.filtered(lambda r: r.period_id == one_period)
            return new_list

        if not self:
            return

        one_period = self.env.context.get('one_period')
        periods = get_period_list(self, one_period=one_period)
        # logger.info(u'!!!! Calculating amounts for %d periods - %s [%s] ::: %d' % (len(self), repr(self.ids), repr(one_period and one_period.ids or []), len(periods)))

        for period in periods:
            y_m = y_m_calc(period.period_id.date_start)
            period_write = {}
            if y_m in fixed_amounts and float_compare(period.amount_fixed, fixed_amounts[y_m], precision_digits=2):
                period_write['amount_fixed'] = float_round(fixed_amounts[y_m], precision_digits=2)
            if y_m in engaged_amounts and float_compare(period.amount_engaged, engaged_amounts[y_m], precision_digits=2):
                period_write['amount_engaged'] = float_round(engaged_amounts[y_m], precision_digits=2)
            if y_m in invoiced_amounts and float_compare(period.amount_invoiced, invoiced_amounts[y_m], precision_digits=2):
                period_write['amount_invoiced'] = float_round(invoiced_amounts[y_m], precision_digits=2)
            if y_m in remaining_amounts and float_compare(period.amount_remaining, remaining_amounts[y_m], precision_digits=2):
                period_write['amount_remaining'] = float_round(remaining_amounts[y_m], precision_digits=2)
            if y_m in pl_fixed_amounts and float_compare(period.profit_loss_amount_fixed, pl_fixed_amounts[y_m], precision_digits=2):
                period_write['profit_loss_amount_fixed'] = float_round(pl_fixed_amounts[y_m], precision_digits=2)
            if y_m in pl_engaged_amounts and float_compare(period.profit_loss_amount_engaged, pl_engaged_amounts[y_m], precision_digits=2):
                period_write['profit_loss_amount_engaged'] = float_round(pl_engaged_amounts[y_m], precision_digits=2)
            if y_m in pl_invoiced_amounts and float_compare(period.profit_loss_amount_invoiced, pl_invoiced_amounts[y_m], precision_digits=2):
                period_write['profit_loss_amount_invoiced'] = float_round(pl_invoiced_amounts[y_m], precision_digits=2)
            if y_m in pl_remaining_amounts and float_compare(period.profit_loss_amount_remaining, pl_remaining_amounts[y_m], precision_digits=2):
                period_write['profit_loss_amount_remaining'] = float_round(pl_remaining_amounts[y_m], precision_digits=2)
            if self.env.context.get('warn_if_different') and period_write:
                period_write['last_error_date'] = datetime.now().strftime(DF)
            if period_write:
                period.write(period_write)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
