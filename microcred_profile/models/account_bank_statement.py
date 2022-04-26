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

from odoo import models, fields, api, _
from collections import defaultdict
from odoo.tools import float_compare, DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin', 'account.bank.statement']
    _name = 'account.bank.statement'

    state = fields.Selection(selection=[
        ('open', 'Draft'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('confirm', 'Reconciled')
    ], deprecated=True)
    microcred_state = fields.Selection(selection=[
        ('open', 'Draft'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('confirm', 'Reconciled')
    ], string='State', tracking=True, store=True, compute='_compute_microcred_state')
    balance_start = fields.Monetary(tracking=True)
    balance_end_real = fields.Monetary(tracking=True)
    balance_end = fields.Monetary(tracking=True)
    payment_authorisor_id = fields.Many2one(
        comodel_name='res.users',
        string='Payment authorisation user',
        help='The user authorising the payment.')
    payment_validator_id = fields.Many2one(
        comodel_name='res.users',
        string='Payment validation user',
        help='The user validating the payment of the statement.')
    payment_authorised_date = fields.Date(string='Order validation date', help='The authorisation date.')
    payment_validate_date = fields.Date(string='Budget validation date', help='The validation date.')

    @api.depends('state')
    def _compute_microcred_state(self):
        if not self.env.context.get('no_microcred_state_change'):
            for statement in self:
                statement.microcred_state = statement.state
        else:
            for statement in self:
                statement.microcred_state = statement.microcred_state

    
    def check_budget_amounts(self):
        for statement in self:
            rounding_precision = statement.company_id.currency_id.rounding
            amounts = defaultdict(float)
            for line in statement.line_ids:
                if line.budget_element_id:
                    amounts[line.budget_element_id] -= line.amount  # Negative for purchases
                else:
                    raise UserError(_('All statement lines must have budget elements.'))
            for budget_element in amounts:
                am = budget_element.amount_engaged + budget_element.amount_invoiced + amounts[budget_element]
                if float_compare(am, budget_element.amount_fixed, precision_rounding=rounding_precision) > 0:
                    raise UserError(_(
                        'By validating this invoice,'
                        ' you will go over-budget'
                        ' (budget line: %s, amount'
                        ' remaining: %.2f, over-budget by %.2f).'
                    ) % (budget_element.name,
                         budget_element.amount_remaining,
                         am - budget_element.amount_fixed))

    
    def validate_statement(self):
        self.check_budget_amounts()
        self.write({
            'state': 'validated',
            'payment_authorisor_id': self.env.user.id,
            'payment_authorised_date': datetime.today().strftime(DF),
        })

    
    def pay_statement(self):
        self.check_budget_amounts()
        self.write({
            'state': 'paid',
            'payment_validator_id': self.env.user.id,
            'payment_validate_date': datetime.today().strftime(DF),
        })

    
    def button_confirm_bank(self):
        statements = self.filtered(lambda r: r.state == 'paid')
        statements.with_context({'no_microcred_state_change': True}).write({'state': 'open'})
        ret = super(AccountBankStatement, statements).button_confirm_bank()
        statements.write({'microcred_state': 'confirm'})
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
