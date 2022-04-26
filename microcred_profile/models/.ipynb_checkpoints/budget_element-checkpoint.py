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

from odoo import models, api, fields, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, float_is_zero, float_compare
from collections import defaultdict
import logging
logger = logging.getLogger('microcred_profile')


class BudgetElement(models.Model):
    _inherit = ['budget.element', 'account.axis.tag.wrapper']
    _name = 'budget.element'
    _order = 'sequence asc, name asc'

    programme_tag_ids = fields.Many2many(comodel_name='budget.element.tag', relation='budget_element_programme_tag_rel', domain=[('type', '=', 'programme')], string='Programme tag', help='', deprecated=True)
    finance_tag_ids = fields.Many2many(comodel_name='budget.element.tag', relation='budget_element_financie_tag_rel', domain=[('type', '=', 'finance')], string='Finance tag', help='', deprecated=True)
    tag_ids = fields.Many2many(comodel_name='budget.element.tag', domain=[('type', '=', 'other')], string='Other tag', help='', deprecated=True)
    # all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' element Tags', help='Select the tags.')
    child_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags9', store=True, compute='_compute_child_tag_ids',
                                     relation='budget_element_child_tag_rel', help='This contains the axis tags for this purchase order and its lines.')
    date_planned = fields.Date(string='Date planned', help='Enter the planned date of this expense.')
    axis_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string=' Axis tags10 for the budget element', help='This contains the axis tags for this budget element.', deprecated=True)
    budget_department_id = fields.Many2one('budget.element', string='Budget department', help='Select the budgetary department.', domain=[('type', '=', 'department')], )
    personnel_ids = fields.One2many('budget.element.personnel', 'budget_id', string='Personnel', help='Enter the employees required for this project.')
    reinvoiceable = fields.Boolean(string='Reinvoiceable', help='Check this box if expenses are to be reinvoiced to this partner.')
    user_can_modify = fields.Boolean(string='User can view', compute='_get_user_can_view', search='_find_user_can_view',)
    budget_line_type_id = fields.Many2one('budget.line.type', string='Line type', help='Select the budget line type.')
    period_detail_ids = fields.One2many('budget.element.period', 'budget_element_id', string='Period details', help='Set the details per period.', copy=False)
    has_manual_periods = fields.Boolean(string='Has manual periods', help='If checked, this budget element has manual periods.', store=True, compute='_get_manual_change',)
    amount_engaged = fields.Float(string='Engaged amount', digits=("Account"), help='The engaged amount.', compute=False, readonly=True, copy=False, )
    amount_invoiced = fields.Float(string='Invoiced amount', digits=("Account"), help='The invoiced amount.', compute=False, readonly=True, copy=False, )
    amount_remaining = fields.Float(string='Remaining amount', digits=("Account"), help='The amount remaining.', compute=False, readonly=True, copy=False, )
    move_line_ids = fields.One2many(comodel_name='account.move.line', inverse_name='budget_element_id', string='Account moves', help='Account moves linked to this budget element.', copy=False)
    account_move_count = fields.Integer(string='Account Moves', help='The number of account moves.', compute='_get_move_count', )
    budget_line_ids = fields.One2many('budget.element', 'budget_id', string='Budget lines', help='Select budget lines.', domain=[('type_id.type', '=', 'budget_line'), ('user_can_modify', '=', True)], copy=False)
    budget_detail_ids = fields.One2many('budget.element', 'budget_id', string='Budget details', help='Select budget details.', domain=[('type_id.type', '=', 'budget_detail'), ('user_can_modify', '=', True)], copy=False)
    child_budget_ids = fields.One2many('budget.element', 'budget_id', string='Child Budgets', help='Child budgets', copy=False)
    subtype_id = fields.Many2one(comodel_name='budget.element.subtype', string='budget Subtype', help='The budget element subtype.')
    subtype = fields.Selection(selection=[('simple', 'Simple'), ('detailed', 'Detailed'), ('amortised', 'Amortised'), ('generated', 'Generated')],
                               string=' Subtype element', readonly=True, help='Select the subtype.', related='subtype_id.subtype')
    asset_category_id = fields.Many2one(comodel_name='account.asset', string='Asset/Accrued expense type', help='Select the asset or accrued expense.')
    amortisation_time = fields.Integer(string='Amortisation_time', help='The time for amortisation (months).')
    amortisation_date = fields.Date(string='Amortisation date', help='The date of the start of amortisation.')
    amortisation_element_ids = fields.One2many(comodel_name='budget.element.amortisation', inverse_name='initial_element_id', string='Amortisation lines',
                                               domain=[('asset_id', '=', False)], help='Enter the amortisation lines.', copy=False)
    modification_required = fields.Boolean(string='Modification required')
    profit_loss_amount_fixed = fields.Float(string='P&L Fixed amount', digits=("Account"), help='The P&L fixed amount.', readonly=True, copy=False, )
    profit_loss_amount_initial = fields.Float(string='P&L Initial amount', digits=("Account"), help='The P&L initial amount.', readonly=True, copy=False)
    profit_loss_amount_engaged = fields.Float(string='P&L Engaged amount', digits=("Account"), help='The P&L engaged amount.', readonly=True, copy=False)
    profit_loss_amount_invoiced = fields.Float(string='P&L Invoiced amount', digits=("Account"), help='The P&L invoiced amount.', readonly=True, copy=False)
    profit_loss_amount_remaining = fields.Float(string='P&L Remaining amount', digits=("Account"), help='The P&L amount remaining.', readonly=True, copy=False)
    sequence = fields.Integer(string='budget Sequence', help='Sequence', compute='_compute_sequence', store=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency', related='company_id.currency_id', readonly=True)
    carried_from_element_id = fields.Many2one(comodel_name='budget.element', string='Carried from', help='The element from which this element is carried on from', readonly=True, copy=False)
    expensify_code = fields.Char(string='Expensify code',  help='Enter Expensify\'s code.')
    error_text = fields.Char(string='Error text', help='Any errors in the budget element')
    company_id = fields.Many2one(index=True)

    @api.depends(
        'budget_line_type_id',
        'budget_line_type_id.sequence',
    )
    def _compute_sequence(self):
        for budget in self:
            budget.sequence = budget.budget_line_type_id.sequence or 9999

    @api.depends(
        'all_tag_ids',
        'child_budget_ids.child_tag_ids'
    )
    def _compute_child_tag_ids(self):
        for budget in self:
            budget.child_tag_ids = [(6, 0, (budget.all_tag_ids | budget.mapped('child_budget_ids.child_tag_ids')).ids)]

    @api.model
    def default_get(self, fields):
        values = super(BudgetElement, self).default_get(fields)
        if 'user_id' not in values:
            values['user_id'] = self.env.user.id
        if 'subtype_id' not in values:
            values['subtype_id'] = self.env['budget.element.subtype'].search([('subtype', '=', 'simple')]).id

        return values

    
    def update_pl_element_amounts(self):
        def y_m_calc(date):
            return date[0:7]

        self.ensure_one()
        pl_fixed_amounts = defaultdict(float)
        pl_engaged_amounts = defaultdict(float)
        pl_invoiced_amounts = defaultdict(float)
        pl_remaining_amounts = defaultdict(float)
        if self.child_budget_ids:  # There are child elements - we get the totals from them
            for child in self.child_budget_ids:
                pl_fixed_amounts[False] += child.profit_loss_amount_fixed
                pl_engaged_amounts[False] += child.profit_loss_amount_engaged
                pl_invoiced_amounts[False] += child.profit_loss_amount_invoiced
                for period in child.period_detail_ids:
                    y_m = period.period_id.date_start
                    pl_fixed_amounts[y_m] += period.profit_loss_amount_fixed
                    pl_engaged_amounts[y_m] += period.profit_loss_amount_engaged
                    pl_invoiced_amounts[y_m] += period.profit_loss_amount_invoiced

        elif self.linked_distribution_id:
            pl_fixed_amounts[False] += self.linked_distribution_id.profit_loss_amount_fixed
            pl_engaged_amounts[False] += self.linked_distribution_id.profit_loss_amount_engaged
            pl_invoiced_amounts[False] += self.linked_distribution_id.profit_loss_amount_invoiced
            for period in self.linked_distribution_id.parent_id.period_detail_ids:
                y_m = y_m_calc(period.period_id.date_start)
                pl_fixed_amounts[y_m] += (period.profit_loss_amount_fixed * self.linked_distribution_id.percentage) / 100
                pl_engaged_amounts[y_m] += (period.profit_loss_amount_engaged * self.linked_distribution_id.percentage) / 100
                pl_invoiced_amounts[y_m] += (period.profit_loss_amount_invoiced * self.linked_distribution_id.percentage) / 100

        else:
            # Calculate P&L engaged amount
            subtype = self.subtype
            if subtype == 'generated':
                if self.carried_from_element_id:
                    subtype = 'amortised'
                else:
                    subtype = 'simple'

            if subtype == 'simple':
                pl_fixed_amounts[False] = self.amount_fixed
                pl_engaged_amounts[False] = self.amount_engaged
                pl_invoiced_amounts[False] = self.amount_invoiced
                for period in self.period_detail_ids:
                    y_m = y_m_calc(period.period_id.date_start)
                    pl_fixed_amounts[y_m] = period.amount_fixed
                    pl_engaged_amounts[y_m] = period.amount_engaged
                    pl_invoiced_amounts[y_m] = period.amount_invoiced

            else:
                # print "Recalculating P&L"
                account_lines = self.env['account.move.line'].sudo().search([
                    ('budget_element_id', '=', self.id),
                    ('date', '>=', self.date_start),
                    ('date', '<=', self.date_end),
                ], order="debit, credit")
                for line in account_lines:
                    line_amount = (line.debit - line.credit)
                    if line.move_id.asset_id and line.move_id.state == 'posted':  # This is linked to an asset - this gets set to the profit and loss
                        pl_invoiced_amounts[False] += line_amount
                        pl_invoiced_amounts[line.date[0:7]] += line_amount

                asset_lines = self.env['account.asset'].search([
                    ('budget_element_id', '=', self.id),
                    ('move_check', '=', False),
                    ('asset_id.state', 'not in', ('draft', 'cancel')),
                    ('depreciation_date', '>=', self.date_start),
                    ('depreciation_date', '<=', self.date_end)
                ])
                for asset_line in asset_lines:
                    pl_engaged_amounts[False] += asset_line.amount
                    pl_engaged_amounts[asset_line.depreciation_date[0:7]] += asset_line.amount

                if self.carried_from_element_id:
                    # We have to calculate the P&L fixed
                    pl_fixed_amounts[False] = pl_engaged_amounts[False]
                    for period in self.period_detail_ids:
                        y_m = y_m_calc(period.period_id.date_start)
                        pl_fixed_amounts[y_m] = pl_engaged_amounts[y_m]
                else:
                    pl_fixed_amounts[False] = self.profit_loss_amount_fixed
                    for period in self.period_detail_ids:
                        y_m = y_m_calc(period.period_id.date_start)
                        pl_fixed_amounts[y_m] = period.profit_loss_amount_fixed

        pl_remaining_amounts[False] = pl_fixed_amounts[False] - (pl_engaged_amounts[False] + pl_invoiced_amounts[False])
        for period in self.period_detail_ids:
            y_m = y_m_calc(period.period_id.date_start)
            pl_remaining_amounts[y_m] = pl_fixed_amounts[y_m] - (pl_engaged_amounts[y_m] + pl_invoiced_amounts[y_m])
            period_write = {}
            if pl_fixed_amounts[y_m] != period.profit_loss_amount_fixed:
                period_write['profit_loss_amount_fixed'] = pl_fixed_amounts[y_m]
            if pl_engaged_amounts[y_m] != period.profit_loss_amount_engaged:
                period_write['profit_loss_amount_engaged'] = pl_engaged_amounts[y_m]
            if pl_invoiced_amounts[y_m] != period.profit_loss_amount_invoiced:
                period_write['profit_loss_amount_invoiced'] = pl_invoiced_amounts[y_m]
            if pl_remaining_amounts[y_m] != period.profit_loss_amount_remaining:
                period_write['profit_loss_amount_remaining'] = pl_remaining_amounts[y_m]
            if period_write:
                period.write(period_write)

        self.write({
            'profit_loss_amount_fixed': pl_fixed_amounts[False],
            'profit_loss_amount_engaged': pl_engaged_amounts[False],
            'profit_loss_amount_invoiced': pl_invoiced_amounts[False],
            'profit_loss_amount_remaining': pl_remaining_amounts[False]
        })

    
    def calculate_element_amounts(self, purchase_order_states):
        def y_m_calc(date):
            return date

        def get_period_list(original_list, one_period=False):
            new_list = original_list
            if one_period:
                new_list = new_list.filtered(lambda r: r.period_id == one_period)
            return new_list

        self.ensure_one()
        one_period = self.env.context.get('one_period')
        fixed_amounts = defaultdict(float)
        engaged_amounts = defaultdict(float)
        invoiced_amounts = defaultdict(float)
        remaining_amounts = defaultdict(float)
        pl_fixed_amounts = defaultdict(float)
        pl_engaged_amounts = defaultdict(float)
        pl_invoiced_amounts = defaultdict(float)
        pl_remaining_amounts = defaultdict(float)
        if self.child_budget_ids:  # There are child elements - we get the totals from them
            for child in self.child_budget_ids:
                if self.type == 'budget_line':
                    fixed_amounts[False] += child.amount_fixed
                engaged_amounts[False] += child.amount_engaged
                invoiced_amounts[False] += child.amount_invoiced
                remaining_amounts[False] += child.amount_remaining
                pl_fixed_amounts[False] += child.profit_loss_amount_fixed
                pl_engaged_amounts[False] += child.profit_loss_amount_engaged
                pl_invoiced_amounts[False] += child.profit_loss_amount_invoiced

                for period in get_period_list(child.period_detail_ids, one_period=one_period):
                    y_m = y_m_calc(period.period_id.date_start)
                    if self.type == 'budget_line':
                        fixed_amounts[y_m] += period.amount_fixed
                    engaged_amounts[y_m] += period.amount_engaged
                    invoiced_amounts[y_m] += period.amount_invoiced
                    remaining_amounts[y_m] += period.amount_remaining
                    pl_fixed_amounts[y_m] += period.profit_loss_amount_fixed
                    pl_engaged_amounts[y_m] += period.profit_loss_amount_engaged
                    pl_invoiced_amounts[y_m] += period.profit_loss_amount_invoiced

            if self.type != 'budget_line':
                fixed_amounts[False] = self.amount_fixed

                for period in get_period_list(self.period_detail_ids, one_period=one_period):
                    y_m = y_m_calc(period.period_id.date_start)
                    fixed_amounts[y_m] = period.amount_fixed

        elif self.linked_distribution_id:
            fixed_amounts[False] += self.linked_distribution_id.amount_fixed or self.linked_distribution_id.amount_calculated
            engaged_amounts[False] += self.linked_distribution_id.amount_engaged
            invoiced_amounts[False] += self.linked_distribution_id.amount_invoiced
            remaining_amounts[False] += self.linked_distribution_id.amount_fixed + (engaged_amounts[False] + invoiced_amounts[False])
            pl_fixed_amounts[False] += self.linked_distribution_id.profit_loss_amount_fixed
            pl_engaged_amounts[False] += self.linked_distribution_id.profit_loss_amount_engaged
            pl_invoiced_amounts[False] += self.linked_distribution_id.profit_loss_amount_invoiced

            for period in get_period_list(self.linked_distribution_id.parent_id.period_detail_ids, one_period=one_period):
                y_m = y_m_calc(period.period_id.date_start)
                fixed_amounts[y_m] += (period.amount_fixed * self.linked_distribution_id.percentage) / 100
                engaged_amounts[y_m] += (period.amount_engaged * self.linked_distribution_id.percentage) / 100
                invoiced_amounts[y_m] += (period.amount_invoiced * self.linked_distribution_id.percentage) / 100
                pl_fixed_amounts[y_m] += (period.profit_loss_amount_fixed * self.linked_distribution_id.percentage) / 100
                pl_engaged_amounts[y_m] += (period.profit_loss_amount_engaged * self.linked_distribution_id.percentage) / 100
                pl_invoiced_amounts[y_m] += (period.profit_loss_amount_invoiced * self.linked_distribution_id.percentage) / 100

        else:
            fixed_amounts[False] = self.amount_fixed
            for period in get_period_list(self.period_detail_ids, one_period=one_period):
                y_m = y_m_calc(period.period_id.date_start)
                fixed_amounts[y_m] = period.amount_fixed
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
            invoiced_amounts[False] = 0 
            invoiced_amounts[y_m] = 0
            for line in account_lines:
                
                y_m = y_m_calc(line.date)
                line_amount = (line.debit - line.credit)
                if line.account_id.code != '48600000':
                    if line.state != 'draft':
                        invoiced_amounts[False] += line_amount 
                        invoiced_amounts[y_m] += line_amount
                               
                    
                    if line.invoice_line_id in linked_invoice_line_ids:
                        remove_amounts[False] += line_amount
                        remove_amounts[y_m] += line_amount
                    
                else:
                     invoiced_amounts[False] += 0 
                     invoiced_amounts[y_m] += 0
                    
                   
                    
            
                    

            if self.subtype == 'amortised' or (self.subtype == 'generated' and self.carried_from_element_id is not False):
                pl_fixed_amounts[False] = self.profit_loss_amount_fixed
                for period in get_period_list(self.period_detail_ids, one_period=one_period):
                    pl_fixed_amounts[y_m_calc(period.period_id.date_start)] += period.profit_loss_amount_fixed

                # Calculate P&L engaged amount
                asset_lines = self.env['account.asset'].search([
                    ('budget_element_id', '=', self.id),
                    ('asset_id.state', 'not in', ('draft', 'cancel')),
                    ('depreciation_date', '>=', self.date_start),
                    ('depreciation_date', '<=', self.date_end)
                ])
                for asset_line in asset_lines:
                    y_m = y_m_calc(asset_line.depreciation_date)
                    if not asset_line.move_check:
                        pl_engaged_amounts[False] += asset_line.amount
                        pl_engaged_amounts[y_m] += asset_line.amount
                    else:
                        pl_engaged_amounts[False] += 0.0
                        pl_engaged_amounts[y_m] += 0.0

                pl_remaining_amounts[False] = self.profit_loss_amount_fixed - (pl_engaged_amounts[False] + pl_invoiced_amounts[False])
                for period in get_period_list(self.period_detail_ids, one_period=one_period):
                    y_m = y_m_calc(period.period_id.date_start)
                    pl_remaining_amounts[y_m] = period.profit_loss_amount_fixed - (pl_engaged_amounts[y_m] + pl_invoiced_amounts[y_m])

            engaged_amounts[False] = purchased_amounts[False] - remove_amounts[False]
            remaining_amounts[False] = self.amount_fixed - (engaged_amounts[False] + invoiced_amounts[False])
            for period in get_period_list(self.period_detail_ids, one_period=one_period):
                y_m = y_m_calc(period.period_id.date_start)
                engaged_amounts[y_m] = purchased_amounts[y_m] - remove_amounts[y_m]
                remaining_amounts[y_m] = period.amount_fixed - (engaged_amounts[y_m] + invoiced_amounts[y_m])

        if self.subtype == 'simple' or (self.subtype == 'generated' and not self.carried_from_element_id):
            pl_fixed_amounts[False] = self.amount_fixed
            pl_engaged_amounts[False] = engaged_amounts[False]
            pl_invoiced_amounts[False] = invoiced_amounts[False]
            pl_remaining_amounts[False] = remaining_amounts[False]
            for period in get_period_list(self.period_detail_ids, one_period=one_period):
                y_m = y_m_calc(period.period_id.date_start)
                pl_fixed_amounts[y_m] = period.amount_fixed
                pl_engaged_amounts[y_m] = engaged_amounts[y_m]
                pl_invoiced_amounts[y_m] = invoiced_amounts[y_m]
                pl_remaining_amounts[y_m] = remaining_amounts[y_m]

        return(fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
               pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts)

    
    def calculate_amounts(self):
        """
        Calculate the engaged, invoiced and remaining amounts
        """
        def y_m_calc(date):
            return date[0:7]

        def get_period_list(original_list, one_period=False):
            new_list = original_list
            if one_period:
                new_list = new_list.filtered(lambda r: r.period_id == one_period)
            return new_list

        (purchase_order_states, invoice_states) = self._get_allowed_states()
        if self.env.context.get('do_not_calculate_budgets'):
            return

        one_period = self.env.context.get('one_period')

        # logger.info(u'!!!! Calculating amounts for %d elements - %s [%s]' % (len(self), repr(self.ids), repr(one_period and one_period.ids or [])))
        for element in self:
            (fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
             pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts) = element.calculate_element_amounts(purchase_order_states)

            # Update the periods first as this data is used on the write of the element for parents and linked amounts
            get_period_list(element.period_detail_ids, one_period=one_period).update_if_different(fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                                                                                                  pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts)
            element_write = {}

            if float_compare(element.amount_fixed, fixed_amounts[False], precision_digits=2):
                element_write.update({
                    'amount_fixed': fixed_amounts[False],
                })

            if float_compare(element.amount_engaged, engaged_amounts[False], precision_digits=2) or \
               float_compare(element.amount_invoiced, invoiced_amounts[False], precision_digits=2) or \
               float_compare(element.amount_remaining, remaining_amounts[False], precision_digits=2):
                element_write.update({
                    'amount_engaged': engaged_amounts[False],
                    'amount_invoiced': invoiced_amounts[False],
                    'amount_remaining': remaining_amounts[False]
                })

            if float_compare(element.profit_loss_amount_fixed, pl_fixed_amounts[False], precision_digits=2):
                element_write.update({
                    'profit_loss_amount_fixed': pl_fixed_amounts[False],
                })

            if float_compare(element.profit_loss_amount_engaged, pl_engaged_amounts[False], precision_digits=2) or \
               float_compare(element.profit_loss_amount_invoiced, pl_invoiced_amounts[False], precision_digits=2) or \
               float_compare(element.profit_loss_amount_remaining, pl_remaining_amounts[False], precision_digits=2):
                element_write.update({
                    'profit_loss_amount_engaged': pl_engaged_amounts[False],
                    'profit_loss_amount_invoiced': pl_invoiced_amounts[False],
                    'profit_loss_amount_remaining': pl_remaining_amounts[False]
                })
            if element_write:
                element.write(element_write)

    
    def _get_move_count(self):
        """
        Calculate the number of invoices and purchases
        """
        for element in self.sudo():
            element_ids = element.mapped('budget_line_ids.budget_detail_ids.id') + element.mapped('budget_line_ids.id') + element.mapped('budget_detail_ids.id') + element.mapped('id')

            move_ids = self.env['account.move.line'].search([('budget_element_id', 'in', element_ids)]).ids
            element.account_move_count = len(move_ids)

    
    def calculate_invoiced_amount(self):
        """
        Calculate the invoiced amount
        """
        self.ensure_one()
        amount = 0.0
        element = self
        if element.type in ('budget_line', 'budget_detail'):
            if not element.linked_distribution_id:
                # Calculate from purchase order lines
                all_element_ids = [element.id]
                all_element_ids.extend(element.mapped('budget_detail_ids.id'))
                amount = 0.0

                # Non-invoiced account move lines
                account_lines = self.env['account.move.line'].sudo().search([
                    ('budget_element_id', 'in', all_element_ids),
                ], order="debit, credit")
                for line in account_lines:
                    line_amount = (line.debit - line.credit)
                    if line.move_id and line.move_id.type in ('out_refund', 'in_refund'):
                        pass
                    amount += line_amount

            else:
                amount = element.linked_distribution_id.amount_invoiced

        else:
            # Calculate from budget lines (sub-budgets are included as budget lines)
            # Budget lines
            for line in element.budget_line_ids:
                amount += line.calculate_invoiced_amount()

        return amount

    @api.depends(
        # Itself
        'move_line_ids.credit',
        'move_line_ids.debit',
        'move_line_ids.budget_element_id',
        # Budget lines
        'budget_line_ids',
        'budget_line_ids.amount_invoiced',
        'budget_line_ids.move_line_ids.credit',
        'budget_line_ids.move_line_ids.debit',
        'budget_line_ids.move_line_ids.budget_element_id',
        # Budget details
        'budget_detail_ids',
        'budget_detail_ids.amount_invoiced',
        'budget_detail_ids.move_line_ids.credit',
        'budget_detail_ids.move_line_ids.debit',
        'budget_detail_ids.move_line_ids.budget_element_id',
        # Budget details of budget lines
        'budget_line_ids.budget_detail_ids',
        'budget_line_ids.budget_detail_ids.amount_invoiced',
        'budget_line_ids.budget_detail_ids.move_line_ids.credit',
        'budget_line_ids.budget_detail_ids.move_line_ids.debit',
        'budget_line_ids.budget_detail_ids.move_line_ids.budget_element_id',
        # Linked distributions
        'linked_distribution_id',
        'linked_distribution_id.amount_invoiced',
    )
    def _get_invoiced_amount(self):
        """
        Calculate the invoiced amount
        """
        for element in self:
            element.amount_invoiced = element.calculate_invoiced_amount()

    @api.depends(
        'period_detail_ids',
        'period_detail_ids.has_manual_change'
    )
    def _get_manual_change(self):
        for element in self:
            element.has_manual_periods = len(element.period_detail_ids.filtered(lambda r: r.has_manual_change)) > 0

    
    def _find_user_can_view(self, operator, operand):
        if operator == '=' and operand is True:
            if self.env.user.id == SUPERUSER_ID:
                return []
            if self.env.ref('microcred_profile.group_microcred_admin') in self.env.user.groups_id or \
               self.env.ref('microcred_profile.group_microcred_accountant') in self.env.user.groups_id or \
               self.env.ref('microcred_profile.group_microcred_head_finance') in self.env.user.groups_id or \
               self.env.ref('microcred_profile.group_microcred_cost_control') in self.env.user.groups_id:
                budgets = self.env['budget.element'].search([('company_id', 'in', self.env.user.company_ids.ids)])
                if not budgets:
                    return [('id', '=', 0)]
                return [('id', 'in', budgets.ids)]
            budgets = self.env['budget.element']
            budgets += budgets.search([('user_id', 'in', self.ids), ('company_id', '=', self.env.user.company_id.id)])
            budgets += budgets.search([('budget_department_id.user_id', 'in', self.ids), ('company_id', 'in', self.env.user.company_ids.ids)])
            budgets += budgets.search([('message_partner_ids', 'in', self.env.user.partner_id.ids), ('company_id', 'in', self.env.user.company_ids.ids)])
            if not budgets:
                return [('id', '=', 0)]

            return [('id', 'in', budgets.ids)]

        return [('id', '=', 0)]

    
    def _get_user_can_view(self):
        """
        Test if the user can view the budget data
        """
        for element in self:
            can_modify = False
            if self.env.user.id == SUPERUSER_ID or \
               self.env.user == element.user_id or \
               self.env.user == element.budget_department_id.user_id:
                can_modify = True
            elif self.env.ref('microcred_profile.group_microcred_admin') in self.env.user.groups_id or \
                    self.env.ref('microcred_profile.group_microcred_accountant') in self.env.user.groups_id or \
                    self.env.ref('microcred_profile.group_microcred_head_finance') in self.env.user.groups_id or \
                    self.env.ref('microcred_profile.group_microcred_cost_control') in self.env.user.groups_id:
                can_modify = True
            elif self.env.ref('microcred_profile.group_microcred_project_manager') in self.env.user.groups_id or \
                    self.env.ref('microcred_profile.group_microcred_department_manager') in self.env.user.groups_id:
                if self.env.user.partner_id in element.message_partner_ids:
                    can_modify = True

            element.user_can_modify = can_modify

    @api.onchange('project_id')
    def onchange_project_id(self):
        """
        Set the manager to that of the department's head
        """
        ret = super(BudgetElement, self).onchange_project_id()
        if self.project_id:
            if self.project_id.date_start or self.project_id.date:
                self.date_start = self.project_id.date_start
                self.date_end = self.project_id.date

        return ret

    
    def create_budget_department_line(self):
        """
        Add the affected budget to budget_department_id if not in the list
        """
        for budget in self:
            if budget.type_id in ('project', 'periodic'):
                found = False
                percentage = 0.0
                for distribution in budget.distribution_cost_ids:
                    if distribution.child_id == budget.budget_department_id:
                        found = True
                        break
                    else:
                        percentage += distribution.percentage  # TODO : Manage fixed amounts...

                if not found:  # We need to add a new distribution
                    new_vals = {
                        'parent_id': budget.id,
                        'child_id': budget.budget_department_id.id,
                        'percentage': 100.0 - percentage,
                    }
                    budget.distribution_cost_ids.create(new_vals)

    
    def check_personnel(self):
        """
        Check that all personnel have budget lines and create/modify one if necessary
        """
        for budget in self:
            amount = 0.0
            personnel_line = budget.search([('is_readonly', '=', True), ('linked_distribution_id', '=', False)], limit=1)
            for personnel in budget.personnel_ids:
                if not personnel.budget_line_id or personnel.budget_line_id == personnel_line:
                    amount += personnel.price_subtotal

            if amount == 0.0:
                if personnel_line:  # Must delete the personnel line as there is no time
                    personnel_line.with_context({'allow_readonly': True}).unlink()
                    personnel_line = False
            elif personnel_line:  # The line exists - update it
                personnel_line.write({'amount_fixed': amount})
            else:  # Need to create the line
                new_vals = {
                    'budget_id': budget.id,
                    'type_id': self.env.ref('advanced_budget.budget_element_type_line').id,
                    'name': _('Personnel'),
                    'amount_fixed': amount,
                    'user_id': budget.user_id.id,
                    'is_readonly': True,
                }
                personnel_line = self.create(new_vals)

            if personnel_line:
                for personnel in budget.personnel_ids:
                    if not personnel.budget_line_id:
                        personnel.write({'budget_line_id': personnel_line.id})

    
    def add_period_detail(self):
        """
        Add the periods to the budget element
        """
        period_obj = self.env['account.period']
        detail_obj = self.env['budget.element.period']
        (purchase_order_states, invoice_states) = self._get_allowed_states()
        # logger.info(u'Started budget_element add_period_detail %s' % repr(self.ids))
        for element in self:
            # Calculate the number of periods
            if not element.date_start or not element.date_end:
                continue
            periods = []
            start_date = datetime.strptime(str(element.date_start), DF)
            end_date = datetime.strptime(str(element.date_end), DF)
            current_date = start_date + relativedelta(day=1)
            while current_date <= end_date:
                period = period_obj.search([('date_start', '<=', current_date.strftime('%Y-%m-%d')), ('date_end', '>=', current_date.strftime('%Y-%m-%d')), ('company_id', '=', element.company_id.id)])
                if not period:  # Need to create the period
                    period = period_obj.create({
                        'date_start': current_date.strftime('%Y-%m-%d'),
                        'date_end': (current_date + relativedelta(days=40) + relativedelta(day=1) + relativedelta(days=-1)).strftime('%Y-%m-%d'),
                        'company_id': element.company_id.id,
                    })

                if period == self.env.context.get('one_period', period):  # Add the period if we only have oe or none at all
                    periods.append(period)

                current_date = current_date + relativedelta(days=40) + relativedelta(day=1)

            # logger.info(u'Element %d period list %s' % (element.id, repr(periods)))
            amount_to_distribute = 0.0
            pl_amount_to_distribute = 0.0
            total_locked = 0.0
            if not element.has_manual_periods:
                amount_to_distribute = element.amount_fixed
                pl_amount_to_distribute = element.profit_loss_amount_fixed
                details = element.period_detail_ids
                # logger.info(u'Element %d period phase B' % (element.id))
                details.filtered(lambda r: r.period_id.state == 'open').write({'amount_fixed': 0.0})  # Clear all open periods (in case the date has been reduced)
                # logger.info(u'Element %d period phase C' % (element.id))
                locked_details = details.filtered(lambda r: r.period_id.state != 'open')
                # logger.info(u'Element %d period phase D' % (element.id))
                for detail in locked_details:
                    total_locked += detail.amount_fixed
                    amount_to_distribute -= detail.amount_fixed  # Remove locked amounts

            # logger.info(u'Element %d phase 2' % (element.id))

            if amount_to_distribute < 0.0:
                raise UserError(_('The budget element \'%s\' has an amount that is too low (%.2f < %.2f) as there are locked periods.') % (element.name, element.amount_fixed, total_locked))

            budget_amounts = {}
            if pl_amount_to_distribute:
                tmp_budget_amounts = element.calculate_monthly_amortisation()
                for key in sorted(tmp_budget_amounts):
                    budget_amounts[(datetime.strftime(key[0], DF), datetime.strftime(key[1], DF))] = tmp_budget_amounts[key]

            # logger.info(u'Element %d phase 3' % (element.id))
            # Create any necessary details
            cur_period = 1
            cur_distribute_count = 1
            running_total = 0.0
            while cur_period <= len(periods):
                period = periods[cur_period - 1]
                period_detail = detail_obj.search([('period_id', '=', period.id), ('budget_element_id', '=', element.id)])
                amount = 0.0
                if (not period_detail or period_detail.period_id.state == 'open'):
                    if amount_to_distribute:
                        amount = round(((amount_to_distribute * cur_distribute_count) / (len(periods) - len(locked_details))), 2) - running_total
                        running_total += amount
                        cur_distribute_count += 1

                if not period_detail:
                    # Need to create detail
                    detail_obj.create({
                        'budget_element_id': element.id,
                        'period_id': period.id,
                        'amount_fixed': amount,
                    })
                else:
                    period_detail.amount_fixed = amount

                cur_period += 1

            # logger.info(u'Element %d phase 4' % (element.id))

            (fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
             pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts) = element.calculate_element_amounts(purchase_order_states)
            element.period_detail_ids.update_if_different(fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                                                          pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts)
        # logger.info(u'Started budget_element add_period_detail %s' % repr(self.ids))

    @api.model
    def create(self, vals):
        """
        Add the affected budget to budget_department_id if not in the list
        """
        if 'amount_fixed' in vals:
            if 'amount_initial' not in vals:
                if vals.get('budget_id'):
                    parent = self.browse(vals['budget_id'])
                    if parent.state == 'draft':
                        vals['amount_initial'] = vals['amount_fixed']

            if 'amount_remaining' not in vals:
                vals['amount_remaining'] = vals['amount_fixed']

        if 'profit_loss_amouint_fixed' in vals:
            if 'profit_loss_amount_initial' not in vals:
                vals['profit_loss_amount_initial'] = vals['profit_loss_amount_fixed']

            if 'profit_loss_amount_remaining' not in vals:
                vals['profit_loss_amount_remaining'] = vals['profit_loss_amount_fixed']

        if 'all_tag_ids' not in vals:
            tag_list = defaultdict(list)
            if 'budget_line_type_id' in vals:
                budget_line_type = self.env['budget.line.type'].browse(vals['budget_line_type_id'])
                for tag in budget_line_type.all_tag_ids:
                    tag_list[tag.axis_id.number].append(tag.id)

            if 'budget_id' in vals:
                parent = self.browse(vals['budget_id'])
                for tag in parent.all_tag_ids:
                    if tag.axis_id.number not in tag_list:
                        tag_list[tag.axis_id.number].append(tag.id)

            all_tags = []
            for number in tag_list.keys():
                all_tags.extend(tag_list[number])
            vals['all_tag_ids'] = [(6, 0, all_tags)]

        new_record = super(BudgetElement, self).create(vals)
        if new_record.state != new_record.budget_id.state:
            if new_record.budget_id.state in ('proposition', 'open'):
                new_record.action_propose_budget()
                if new_record.budget_id.state == 'open':
                    new_record.action_open_budget()

        if 'budget_department_id' in vals:
            if vals['budget_department_id']:
                new_record.create_budget_department_line()
                new_record.message_subscribe(partner_ids=[new_record.sudo().budget_department_id.user_id.partner_id.id])

        partner_ids = self.env['res.users'].sudo().search([('autosubscribe_budgets', '=', True)]).mapped('user_group_ids.partner_id').ids
        if partner_ids:
            new_record.sudo().message_subscribe(partner_ids=partner_ids)

        if not new_record.period_detail_ids and new_record.date_start and new_record.date_end:
            new_record.add_period_detail()

        new_record.calculate_amounts()
        new_record.calculate_profit_and_loss()
        if new_record.budget_id:
            new_record.budget_id.calculate_amounts()
            new_record.budget_id.calculate_profit_and_loss()

        return new_record

    
    def write_budget_department_id(self, vals):
        # logger.info(u'Started budget_element write_budget_department_id %s', repr(self.ids))
        if vals['budget_department_id']:
            self.create_budget_department_line()
            for element in self:
                element.message_subscribe(partner_ids=[element.budget_department_id.user_id.partner_id.id])
        if self.mapped('budget_line_ids'):
            self.mapped('budget_line_ids').write({'budget_department_id': vals['budget_department_id']})
        if self.mapped('budget_detail_ids'):
            self.mapped('budget_detail_ids').write({'budget_department_id': vals['budget_department_id']})
        # logger.info(u'Ended budget_element write_budget_department_id %s', repr(self.ids))

    
    def write_amount_fixed(self, vals, old_amounts):
        # logger.info(u'Started budget_element write_amount_fixed %s', repr(self.ids))
        for element in self:
            main_budget = False
            if element.type in ('periodic', 'project'):
                main_budget = element
            elif element.type == 'budget_line':
                main_budget = element.budget_id
            elif element.type == 'budget_detail':
                main_budget = element.budget_id.budget_id
            if main_budget and element.state == 'draft':
                main_budget.message_post(body=_('%s modified from %.2f to %.2f') % (element.name, old_amounts[element], element.amount_fixed))
            if element.asset_category_id:
                new_lines = element.calculate_amortisation()
                lines = []
                for line in element.amortisation_element_ids:
                    for new_line in new_lines:
                        if line.date_start == new_line['date_start']:
                            lines.append((1, line.id, {'amount_amortised': new_line['amount_amortised']}))
                super(BudgetElement, element).write({'amortisation_element_ids': lines})
        # logger.info(u'Ended budget_element write_amount_fixed %s', repr(self.ids))

    
    def write_amount_remaining(self, vals):
        # logger.info(u'Started budget_element write_amount_remaining %s', repr(self.ids))
        (purchase_order_states, invoice_states) = self._get_allowed_states()
        for element in self:
            (fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts, pl_fixed_amounts,
             pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts) = element.calculate_element_amounts(purchase_order_states)
            super(BudgetElement, element).write({
                # 'amount_fixed': fixed_amounts[False],
                'amount_engaged': engaged_amounts[False],
                'amount_invoiced': invoiced_amounts[False],
                'amount_remaining': remaining_amounts[False],
                'profit_loss_amount_fixed': pl_fixed_amounts[False],
                'profit_loss_amount_engaged': pl_engaged_amounts[False],
                'profit_loss_amount_invoiced': pl_invoiced_amounts[False],
                'profit_loss_amount_remaining': pl_remaining_amounts[False],
            })
            element.period_detail_ids.update_if_different(fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                                                          pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts)
        # logger.info(u'Ended budget_element write_amount_remaining %s', repr(self.ids))

    
    def write_pl(self, vals):
        # logger.info(u'Started budget_element write_pl %s', repr(self.ids))
        for element in self:
            new_vals = {}
            if element.subtype != 'generated':
                pl_fixed = element.calculate_profit_and_loss_element()
                new_vals['profit_loss_amount_fixed'] = pl_fixed
            else:
                pl_fixed = vals.get('profit_loss_amount_fixed', element.profit_loss_amount_fixed)

            pl_remaining = pl_fixed - (element.profit_loss_amount_engaged + element.profit_loss_amount_invoiced)
            if pl_remaining != self.profit_loss_amount_remaining:
                new_vals['profit_loss_amount_remaining'] = pl_remaining
            if new_vals:
                super(BudgetElement, element).write(new_vals)
        # logger.info(u'Ended budget_element write_pl %s', repr(self.ids))

    
    def write_extra(self, vals):
        elements = self | self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        # logger.info(u'Started budget_element write_extra %s -> %s', repr(self.ids), repr(elements.ids))
        elements.add_period_detail()
        # logger.info(u'Ended budget_element write_extra %s -> %s', repr(self.ids), repr(elements.ids))

    
    def copy(self, default=None):
        if not default:
            default = {}
        new_elements = self.env['budget.element']
        for element in self:
            new_element = super(BudgetElement, self).copy(default=default)
            new_elements |= new_element
            new_write = {}
            if new_element.company_id != element.company_id:
                new_tags = []
                for tag in element.all_tag_ids:
                    new_tag = tag.get_company_equivalent(new_element.company_id)
                    if new_tag:
                        new_tags.append(new_tag.id)
                if new_tags:
                    new_write['all_tag_ids'] = [(6, 0, new_tags)]
                else:
                    new_write['all_tag_ids'] = [(5, 0, 0)]
                if new_element.distribution_budget_ids:
                    new_element.distribution_budget_ids.unlink()
            else:
                # Only copy if it's the same company (otherwise, it's impossible...)
                if element.distribution_budget_ids and not new_element.distribution_budget_ids:
                    for distribution in element.distribution_budget_ids:
                        distribution.copy({
                            'parent_id': new_element.id
                        })

            if element.distribution_cost_ids and not new_element.distribution_cost_ids:
                for distribution in element.distribution_cost_ids:
                    distribution.copy({
                        'parent_id': new_element.id
                    })

            if new_write:
                new_element.write(new_write)

        return new_elements

    
    def write(self, vals):
        """
        Add the affected budget to budget_department_id if not in the list
        Set all tag ids (bug in standard for multiple many2many fields pointing to same model ?)
        Also, if it's a budget line or a budget detail, log the changes if in draft state
        """
        def y_m_calc(date):
            return date[0:7]

        old_amounts = {}
        for element in self:
            old_amounts[element] = element.amount_fixed

        if 'subtype_id' in vals:
            for element in self:
                if element.subtype_id.id != vals['subtype_id']:
                    if self.move_line_ids or\
                       self.purchase_line_ids or\
                       self.invoice_line_ids or\
                       self.budget_detail_ids or\
                       self.env['account.asset'].search([('budget_element_id', '=', element.id)]):
                        element_type = _('budget element')
                        if element.type == 'budget_line':
                            element_type = _('line')
                        elif element.type == 'budget_detail':
                            element_type = _('detail')
                        raise UserError(_('You cannot modify the subtype of the {type} \'{name}\' as there are already journal items, budget details, invoices, purchase orders or assets associated with it.').format(type=element_type, name=element.name))

        if 'amortisation_element_ids' in vals:
            has_deletion = False
            new_elements = []
            for element in vals['amortisation_element_ids']:
                if element[0] == 2:
                    has_deletion = True
                else:
                    new_elements.append(element)

            if has_deletion:
                self.amortisation_element_ids.unlink()
                vals['amortisation_element_ids'] = new_elements

        # logger.info(u'Started budget_element write %s', repr(self.ids))
        if 'budget_detail_ids' in vals:
            details = vals['budget_detail_ids']
            total_amount = 0
            for detail in details:
                this_amount = 0.0
                if detail[0] in (1, 4):
                    budget_detail = self.browse(detail[1])
                    this_amount = budget_detail.amount_fixed
                if detail[0] == 1:
                    if 'amount_fixed' in detail[2]:
                        this_amount = detail[2]['amount_fixed']
                total_amount += this_amount
            if float_compare(total_amount, self.amount_fixed, precision_digits=2):
                vals['amount_fixed'] = total_amount

        parents = self.env['budget.element']
        if 'budget_id' in vals:
            parents |= self.filtered(lambda r: r.budget_id is not False).mapped('budget_id')

        if 'subtype_id' in vals:
            if vals['subtype_id'] == self.env.ref('microcred_profile.budget_subtype_simple').id:
                vals['asset_category_id'] = False

        vals['error_text'] = False  # This is cleared (and calculated elsewhere)

        ret = super(BudgetElement, self).write(vals)
        if 'period_detail_ids' in vals:
            bad_lines = []
            bad_details = []
            for budget in self:
                total_amount = 0.0
                for period in budget.period_detail_ids:
                    total_amount += period.amount_fixed

                if float_compare(total_amount, budget.amount_fixed, precision_digits=2) != 0:
                    if budget.type == 'budget_line':
                        bad_lines.append('--- {budget.name}'.format(budget=budget))
                    else:
                        bad_details.append('--- {budget.budget_id.name}/{budget.name}'.format(budget=budget))

            if bad_lines or bad_details:
                errors = []
                if bad_lines and bad_details:
                    errors.append(_('The following lines and details have monthly amounts whose totals are not equal to their amounts:'))
                    errors.append(_('- Budget Lines:'))
                    errors.extend(bad_lines)
                    errors.append(_('- Budget Details:'))
                    errors.extend(bad_details)

                elif bad_lines:
                    if len(bad_lines) == 1:
                        errors.append(_('The following line has monthly amounts whose total is not equal to its amounts:'))
                    else:
                        errors.append(_('The following lines have monthly amounts whose totals are not equal to their amounts:'))
                    errors.extend(bad_lines)

                else:
                    if len(bad_details) == 1:
                        errors.append(_('The following detail has monthly amounts whose total is not equal to its amounts:'))
                    else:
                        errors.append(_('The following details have monthly amounts whose totals are not equal to their amounts:'))
                    errors.extend(bad_details)

                raise UserError('\n'.join(errors))

        if 'budget_department_id' in vals:
            self.write_budget_department_id(vals)

        if 'amount_fixed' in vals or self.env.context.get('update_remaining'):
            self.write_amount_fixed(vals, old_amounts)

            if 'amount_remaining' not in vals:
                self.write_amount_remaining(vals)

        if 'user_id' in vals:
            # Subscribe the new user to this budget
            partner_id = self.env['res.users'].sudo().browse(vals['user_id']).partner_id.id
            for element in self:
                element.message_subscribe(partner_ids=[partner_id])
            # Change users for the budget lines
            sub_elements = self.mapped('budget_line_ids') + self.mapped('budget_detail_ids')
            if sub_elements:
                sub_elements.write({'user_id': vals['user_id']})
            # Add this user to all existing purchase orders and invoices which refer to this budget
            for invoice in self.env['account.move.line'].search(['|', ('budget_element_id', 'in', self.ids), ('budget_element_id.budget_department_id', 'in', self.ids)]).mapped('move_id'):
                invoice.message_subscribe(partner_ids=[partner_id])
            for order in self.env['purchase.order.line'].search(['|', ('budget_element_id', 'in', self.ids), ('budget_element_id.budget_department_id', 'in', self.ids)]):
                order.mapped('order_id').message_subscribe(partner_ids=[partner_id])

        if 'profit_loss_amount_fixed' in vals or 'amortisation_element_ids' in vals:
            self.write_pl(vals)

        if ('date_start' in vals or 'date_end' in vals or 'amount_fixed' in vals or 'amortisation_date' in vals or 'amortisation_time' in vals) and 'period_detail_ids' not in vals:
            self.write_extra(vals)

        if 'budget_line_type_id' in vals:
            for element in self:
                new_vals = {}
                if 'name' not in vals:
                    new_vals['name'] = element.budget_line_type_id.name

                tag_list = defaultdict(list)
                if 'budget_line_type_id' in vals:
                    for tag in element.budget_line_type_id.all_tag_ids:
                        tag_list[tag.axis_id.number].append(tag.get_company_equivalent(self.company_id or self.budget_id.company_id or self.budget_id.budget_id.company_id).id)

                if 'budget_id' in vals:
                    for tag in element.budget_id.all_tag_ids:
                        if tag.axis_id.number not in tag_list:
                            tag_list[tag.axis_id.number].append(tag.id)
                else:
                    for tag in element.all_tag_ids:
                        if tag.axis_id.number not in tag_list:
                            tag_list[tag.axis_id.number].append(tag.id)

                all_tags = []
                for number in tag_list.keys():
                    all_tags.extend(tag_list[number])
                new_vals['all_tag_ids'] = [(6, 0, all_tags)]

                if new_vals:
                    element.write(new_vals)

        if 'amount_engaged' in vals or \
           'amount_invoiced' in vals or \
           'amount_remaining' in vals or \
           'amount_fixed' in vals or \
           'profit_loss_amount_engaged' in vals or \
           'profit_loss_amount_invoiced' in vals or \
           'profit_loss_amount_remaining' in vals or \
           'profit_loss_amount_fixed' in vals or \
           'budget_id' in vals or \
           self.env.context.get('update_remaining'):
            parents |= self.filtered(lambda r: r.budget_id is not False).mapped('budget_id')

        if self.mapped('distribution_budget_ids') and (
                'amount_engaged' in vals or
                'amount_invoiced' in vals or
                'amount_remaining' in vals or
                'amount_fixed' in vals or
                'profit_loss_amount_engaged' in vals or
                'profit_loss_amount_invoiced' in vals or
                'profit_loss_amount_remaining' in vals or
                'profit_loss_amount_fixed' in vals):
            self.mapped('distribution_budget_ids').calculate_amounts()

        if parents:
            parents.calculate_amounts()

        if 'all_tag_ids' in vals:
            self.set_axis_fields()

        # logger.info(u'Ended budget_element write %s', repr(self.ids))
        return ret

    
    def unlink(self):
        """
        If it's something other than a budget line or detail, it may need verification
        """
        if self.env.user.id != SUPERUSER_ID:
            check_rights = False
            for element in self:
                if element.state != 'draft':
                    raise UserError(_('Only draft budgets can be deleted.'))
                if element.type in ('periodic', 'project', 'department', 'partner'):
                    check_rights = True

            if check_rights:
                if not (self.env.ref('microcred_profile.group_microcred_admin') in self.env.user.groups_id or
                   self.env.ref('microcred_profile.group_microcred_accountant') in self.env.user.groups_id or
                   self.env.ref('microcred_profile.group_microcred_head_finance') in self.env.user.groups_id or
                   self.env.ref('microcred_profile.group_microcred_cost_control') in self.env.user.groups_id):
                    raise UserError(_('You cannot delete this budget.'))

        recalc_budgets = self.filtered(lambda r: r.budget_id is not False).mapped('budget_id')
        self.mapped('amortisation_element_ids').unlink()
        super(BudgetElement, self).unlink()
        if recalc_budgets:
            recalc_budgets.calculate_amounts()

    
    def _get_allowed_states(self):
        """
        Over-ridden function for getting allowed states in purchase orders and invoices
        """
        return(
            ('purchase', ),
            ('open','paid'),
        )

    
    def action_open_budget(self):
        """
        Set the element and its appropriate lines to 'Open'
        """
        for budget in self:
            if budget.amount_fixed < budget.amount_calculated:
                raise UserError(_('The fixed amount must be equal to or greater than the calculated amount.'))
            if not budget.profit_loss_amount_initial:
                budget.profit_loss_amount_initial = budget.profit_loss_amount_fixed

        super(BudgetElement, self).action_open_budget()

    @api.onchange('date_start', 'date_end')
    def onchange_dates(self):
        if self.mapped('budget_line_ids').filtered('has_manual_periods') or self.mapped('budget_detail_ids').filtered('has_manual_periods') or self.mapped('budget_line_ids.budget_detail_ids').filtered('has_manual_periods'):
            return {
                'warning': {
                    'title': _('Change date warning'),
                    'message': _('At least one budget line or detail has had its monthly period amounts changed. The amounts cannot be recalculated automatically for these lines or details - you must do this manually.'),
                }
            }

    @api.onchange('budget_line_type_id')
    def onchange_budget_line_type(self):
        if self.budget_line_type_id:
            tag_list = defaultdict(list)
            company = self.company_id or self.budget_id.company_id or self.budget_id.budget_id.company_id
            if not company and self.env.context.get('default_company_id'):
                company = self.env['res.company'].browse(self.env.context['default_company_id'])
            if not company:
                company = self.env.user.company_is
            for tag in self.budget_line_type_id.all_tag_ids:
                equivalent_tag = tag.get_company_equivalent(company).id
                if equivalent_tag:
                    tag_list[tag.axis_id.number].append(equivalent_tag)

            if self.all_tag_ids:
                for tag in self.all_tag_ids:
                    if tag.axis_id.number not in tag_list:
                        tag_list[tag.axis_id.number].append(tag.id)

            all_tags = []
            for number in tag_list.keys():
                all_tags.extend(tag_list[number])
            self.all_tag_ids = [(6, 0, all_tags)]

    
    def calculate_planned(self):
        for element in self:
            if element.is_readonly:  # We only do this to calculated elements
                for period in element.period_detail_ids:
                    pass

    
    def calculate_linked_amounts(self, vals=None):
        """
        Calculate the amount in a linked budget line
        """
        if vals is None:
            vals = {}

        for line in self:
            line_vals = {}
            amount_fixed = 0.0
            for detail in line.period_detail_ids:
                amount_fixed += detail.amount_fixed
            line_vals['amount_fixed'] = amount_fixed
            if 'name' in vals:
                line_vals['name'] = vals['name']
            line.sudo().write(line_vals)  # We may not have direct rights to the line...

    
    def get_descendants_invoices_and_purchases(self):
        """
        Get the children (and grand-children) as well as the invoices and purchase orders of this/these budget element(s)
        """
        descendant_elements = self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        budget_elements = self | descendant_elements
        invoices = self.env['account.move.line'].search([('budget_element_id', 'in', budget_elements.ids)]).mapped('move_id')
        purchases = self.env['purchase.order.line'].search([('budget_element_id', 'in', budget_elements.ids)]).mapped('order_id')
        return(descendant_elements, invoices, purchases)

    
    def open_view(self, view_xml_id, model, line_ids=None):
        self.ensure_one()

        element_ids = self.mapped('budget_line_ids.budget_detail_ids.id') + self.mapped('budget_line_ids.id') + self.mapped('budget_detail_ids.id') + self.mapped('id')

        action = self.env.ref(view_xml_id, False)
        action_data = action.read()[0]

        if line_ids is None:
            line_ids = self.env[model].search([('budget_element_id', 'in', element_ids)]).ids

        action_data.update(
            context={
                'target': 'new',
            },
            domain=[('id', 'in', line_ids)],
        )
        return action_data

    
    def view_amortisations(self):
        """
        Amortisations
        """
        self.ensure_one()
        element_ids = self.mapped('budget_line_ids.budget_detail_ids.id') + self.mapped('budget_line_ids.id') + self.mapped('budget_detail_ids.id') + self.mapped('id')
        asset_ids = self.env['account.asset'].search([('budget_element_id', 'in', element_ids)]).mapped('asset_id').filtered(lambda r: r.is_accrued_expense is False).ids
        return self.open_view('account_asset.action_account_asset_asset_form', 'account.asset', line_ids=asset_ids)

    
    def view_accrued_expenses(self):
        """
        Accrued exoenses
        """
        self.ensure_one()
        element_ids = self.mapped('budget_line_ids.budget_detail_ids.id') + self.mapped('budget_line_ids.id') + self.mapped('budget_detail_ids.id') + self.mapped('id')
        asset_ids = self.env['account.asset'].search([('budget_element_id', 'in', element_ids)]).mapped('asset_id').filtered(lambda r: r.is_accrued_expense is True).ids
        return self.open_view('microcred_profile.action_account_asset_accrued_expense_form', 'account.asset', line_ids=asset_ids)

    
    def list_account_moves(self):
        """
        List account moves
        """
        self.ensure_one()
        return self.open_view('account.action_account_moves_all_a', 'account.move.line')

    
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        """
        Subscribe the partner(s) to the budget lines and details, invoices and purchase orders
        """
        ret = super(BudgetElement, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
        (elements, invoices, purchases) = self.get_descendants_invoices_and_purchases()

        if invoices:
            invoices.message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)

        if purchases:
            purchases.message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)

        if elements:
            super(BudgetElement, elements).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)

        return ret

    
    def message_unsubscribe(self, partner_ids=None, channel_ids=None):
        """
        Unsubscribe the partner(s) to the budget lines and details, invoices and purchase orders
        """
        ret = super(BudgetElement, self).message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)
        (elements, invoices, purchases) = self.get_descendants_invoices_and_purchases()

        if invoices:
            invoices.message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)

        if purchases:
            purchases.message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)

        if elements:
            super(BudgetElement, elements).message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)

        return ret

    
    def calculate_depths(self):
        """
        Calculate the depths of all budget elements - returns dictionary of ids and depths
        """
        depths = defaultdict(int)
        cur_depth = 0
        # Get the list of linked budgets
        domain = [('budget_id', '=', False)]
        if self:
            domain = [('id', 'in', self.ids)]

        new_elements = self.search(domain)
        while new_elements and cur_depth < 1000:
            cur_elements = new_elements
            new_elements = self
            for element in cur_elements:
                depths[element.id] = cur_depth
                if element.linked_distribution_id:
                    new_elements += element.linked_distribution_id.parent_id

            new_elements += self.search([
                ('budget_id', 'in', cur_elements.ids),
            ])
            cur_depth += 1

        return (cur_depth, depths)

   # @api.model
   # def _get_tracked_fields(self, updated_fields):
   #     return super(BudgetElement, self.with_context(lang='en_EN'))._get_tracked_fields(updated_fields)

    
    def get_tags(self, axis_number):
        self.ensure_one()
        if self.all_tag_ids:
            return self.all_tag_ids.filtered(lambda r: r.axis_id.number == axis_number)
        else:
            return self.all_tag_ids

    @api.onchange('asset_category_id')
    def onchange_asset_category(self):
        if self.asset_category_id and not self.asset_category_id.is_accrued_expense:
            self.update({
                'amortisation_time': self.asset_category_id.method_number * self.asset_category_id.method_period
            })

    @api.onchange('amount_fixed')
    def onchange_amount_fixed(self):
        if self.subtype == 'amortised':
            new_lines = self.calculate_amortisation()
            lines = [(5, 0, 0)]
            for line in new_lines:
                lines.append((0, 0, line))

            self.amortisation_element_ids = lines

    @api.onchange('amortisation_date', 'amortisation_time')
    def onchange_amortisation(self):
        if self.subtype == 'amortised':
            major_changes = {
                'modification_required': True,
                'amortisation_element_ids': [(5, 0, 0)]
            }
            if not self.amortisation_date:
                major_changes['amortisation_date'] = self.date_start or self.budget_id.date_start or self.budget_id.budget_id.date_start or datetime.strftime(datetime.now(), DF)
            if not self.amortisation_time:
                major_changes['amortisation_time'] = self.asset_category_id.method_number * self.asset_category_id.method_period

            new_lines = self.calculate_amortisation(start_date=self.amortisation_date or major_changes['amortisation_date'], amort_time=self.amortisation_time or major_changes['amortisation_time'])
            lines = [(5, 0, 0)]
            for line in new_lines:
                lines.append((0, 0, line))

            major_changes.update({'amortisation_element_ids': lines})
            self.update(major_changes)

    @api.model
    def calculate_monthly_amortisation(self, start_date=False, amort_time=0.0):
        self.ensure_one()
        budget_amounts = {}
        if self.asset_category_id:
            if not start_date:
                start_date = self.amortisation_date or self.date_start or self.budget_id.date_start or self.budget_id.budget_id.date_start or datetime.strftime(datetime.now(), DF)
            if not amort_time:
                amort_time = self.amortisation_time or self.asset_category_id.method_number * self.asset_category_id.method_period
            date_start = datetime.strptime(str(start_date), DF)
            date_end = date_start + relativedelta(months=amort_time, days=-1)
            all_days = (date_end - date_start).days + 1
            cur_date = date_start + relativedelta(day=1, month=1)
            next_date = cur_date
            prorata_amount = self.amount_fixed / (self.asset_category_id.method_number * self.asset_category_id.method_period)
            remaining = self.amount_fixed or 0.0
            first_key = False
            while cur_date < date_end:
                next_date = cur_date + relativedelta(months=1)
                if next_date > date_start:
                    period_start = cur_date
                    if period_start < date_start:
                        period_start = date_start
                    period_end = next_date + relativedelta(days=-1)
                    if period_end > date_end:
                        period_end = date_end

                    key = (period_start, period_end)

                    if not first_key:
                        first_key = key

                    this_amount = 0.0
                    if self.asset_category_id.daily_prorata:
                        this_days = (period_end - period_start).days + 1
                        if all_days:
                            this_amount = (remaining * this_days) / all_days
                        else:
                            this_amount = 0.0
                        all_days -= this_days
                    elif self.asset_category_id.prorata:
                        # TODO : Somehow use the "official" [incorrect] way of calculating this - it's a complicated method and needs creating an asset to work on - not advised within an on_change...
                        this_amount = prorata_amount
                    else:
                        # TODO : I have no idea how this is calculated otherwise...
                        this_amount = prorata_amount

                    this_amount = (self.company_id.currency_id or self.budget_id.company_id.currency_id or self.budget_id.budget_id.company_id.currency_id or self.env.user.company_id.currency_id).round(this_amount)
                    budget_amounts[key] = this_amount
                    remaining -= this_amount
                cur_date = next_date

            if not float_is_zero(remaining, precision_digits=2):
                budget_amounts[first_key] += remaining

        return budget_amounts

    @api.model
    def calculate_amortisation(self, start_date=False, amort_time=0.0):
        self.ensure_one()
        lines = []
        if self.asset_category_id:
            if not start_date:
                start_date = self.amortisation_date or self.date_start or self.budget_id.date_start or self.budget_id.budget_id.date_start or datetime.strftime(datetime.now(), DF)
            if not amort_time:
                amort_time = self.amortisation_time or self.asset_category_id.method_number * self.asset_category_id.method_period
            element_date_end = self.date_end or self.budget_id.date_end or self.budget_id.budget_id.date_end or datetime.strftime(datetime.now(), DF)
            date_start = datetime.strptime(str(start_date), DF)
            date_end = date_start + relativedelta(months=amort_time, days=-1)
            budget_amounts = self.calculate_monthly_amortisation(start_date=start_date, amort_time=amort_time)

            # Regroup into yearly groups
            monthly_amounts = budget_amounts.copy()
            budget_amounts = {}
            cur_date = date_start + relativedelta(day=1, month=1)
            first_key = False
            while cur_date < date_end:
                next_date = cur_date + relativedelta(years=1)

                period_start = cur_date
                if cur_date < date_start:
                    period_start = date_start
                period_end = next_date + relativedelta(days=-1)
                if period_end > date_end:
                    period_end = date_end

                key = (period_start, period_end)
                if not first_key:
                    first_key = key

                amount = 0.0
                for (month_start, month_end) in monthly_amounts:
                    if month_start >= period_start and month_end <= period_end:
                        amount += monthly_amounts[(month_start, month_end)]
                budget_amounts[key] = amount

                cur_date = next_date

            for period in budget_amounts:
                date_start = period[0].strftime(DF)
                date_end = period[1].strftime(DF)
                budget_element_id = False
                if date_end <= element_date_end:
                    budget_element_id = self.id

                lines.append({
                    'date_start': date_start,
                    'date_end': date_end,
                    'budget_element_id': budget_element_id,
                    'amount_amortised': budget_amounts[period],
                })

        return lines

    
    def calculate_profit_and_loss_element(self):
        self.ensure_one()
        fixed = 0.0
        if self.amortisation_element_ids:
            for amortisation in self.amortisation_element_ids:
                if amortisation.budget_element_id == self:
                    fixed += amortisation.amount_amortised
        return fixed

    
    def calculate_profit_and_loss(self, no_write=False):
        for element in self:
            if element.amortisation_element_ids:
                element.write({
                    'profit_loss_amount_fixed': element.calculate_profit_and_loss_element(),
                })

    @api.onchange('subtype_id')
    def onchange_subtype(self):
        if self.subtype_id.subtype == 'generated' and not self.is_readonly:
            self.subtype_id = False
            return {
                'warning': {
                    'title': _('Selection error'),
                    'message': _('You cannot manually select a generated budget !')
                }
            }

    @api.model
    def check_budget_period_amounts(self):
        # logger.info(u'Started checking amounts...')
        (purchase_order_states, invoice_states) = self._get_allowed_states()

        elements = self.env['budget.element'].search([('child_budget_ids', '=', False), ('linked_distribution_id', '=', False)])
        while elements:
            for element in elements:
                (fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                 pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts) = element.calculate_element_amounts(purchase_order_states)
                element.period_detail_ids.with_context({'warn_if_different': True}).update_if_different(fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                                                                                                        pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts)
            elements = elements.mapped('budget_id')

        elements = self.env['budget.element'].search([('child_budget_ids', '=', False), ('linked_distribution_id', '!=', False)])
        while elements:
            for element in elements:
                (fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                 pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts) = element.calculate_element_amounts(purchase_order_states)
                element.period_detail_ids.with_context({'warn_if_different': True}).update_if_different(fixed_amounts, engaged_amounts, invoiced_amounts, remaining_amounts,
                                                                                                        pl_fixed_amounts, pl_engaged_amounts, pl_invoiced_amounts, pl_remaining_amounts)
            elements = elements.mapped('budget_id')

    @api.onchange('period_detail_ids')
    def onchange_lines_and_details(self):
        total = 0.0
        error_text = ''
        if self.period_detail_ids:
            for line in self.period_detail_ids:
                total += line.amount_fixed

        if float_compare(total, self.amount_fixed, precision_digits=2) != 0:
            error_text = _('The sum of the monthly amounts are not the same as the total amount.')

        self.update({'error_text': error_text})
        
        
    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
