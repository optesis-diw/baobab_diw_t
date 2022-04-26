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

from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo.tools import formatLang


class WizardTransferBudgetAmount(models.TransientModel):
    _name = "wizard.transfer.budget.amount"
    _description = "Transfer budget amount wizard"

    budget_element_src_id = fields.Many2one(comodel_name='budget.element', string='Source budget element', readonly=True)
    transfer_type = fields.Selection(selection=[
        ('new_sibling', 'New sibling (in the same budget)'),
        ('existing_sibling', 'Existing sibling (in the same budget)'),
        ('new_line', 'New budget line (in another budget)'),
        ('existing_line', 'Existing budget line (in another budget)'),
        ('new_detail', 'New budget detail (in another budget line)'),
        ('existing_detail', 'Existing budget detail (in another budget line)'),
        ('new_line_and_detail', 'New budget detail in a new budget line (in another budget)'),
    ], string='Transfer type', required=True, help='Select to where you want to transfer the data.')
    company_src_id = fields.Many2one(comodel_name='res.company', string='Source company', help='The source ompany.')
    company_dst_id = fields.Many2one(comodel_name='res.company', string='Destination company', help='Select the destination company.')
    main_budget_dst_id = fields.Many2one(comodel_name='budget.element', string='Target budget')
    budget_element_dst_id = fields.Many2one(comodel_name='budget.element', string='Target budget element')
    amount_src = fields.Float(string='Amount to transfer', digits=("Account"), help='Enter the amount to transfer.')
    amount_available = fields.Float(string='Amount available', digits=("Account"), readonly=True, help='The amount available to transfer.')
    amount_dst = fields.Float(string='Amount to receive', digits=("Account"), readonly=True, help='The amount that will be recived.')
    currency_src_id = fields.Many2one(comodel_name='res.currency', string='src Currency', help='The source currency', readonly=True)
    currency_dst_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The destination currency', readonly=True)
    transfer_charge = fields.Float(string='Transfer charge', digits=("Account"), help='Enter the transfer charge.')
    different_company = fields.Boolean(string='Different company')
    can_transfer = fields.Boolean(string='Can transfer')

    
    def get_domains(self):
        self.ensure_one()
        domains = {
            'main_budget_dst_id': [('company_id', '=', self.company_dst_id.id), ('state', 'not in', ('close', 'cancel')), ('type', 'in', ('periodic', 'project'))],
        }
        if self.transfer_type == 'existing_sibling':
            domains['budget_element_dst_id'] = [('budget_id', '=', self.budget_element_src_id.budget_id.id), ('is_readonly', '=', False), ('id', '!=', self.budget_element_src_id.id), ('user_can_modify', '=', True)]
        elif self.transfer_type == 'existing_line':
            domains['budget_element_dst_id'] = [('budget_id', '=', self.main_budget_dst_id.id), ('child_budget_ids', '=', False), ('is_readonly', '=', False), ('id', '!=', self.budget_element_src_id.id), ('user_can_modify', '=', True)]
        elif self.transfer_type == 'new_detail':
            domains['budget_element_dst_id'] = [('budget_id', '=', self.main_budget_dst_id.id), ('child_budget_ids', '!=', False), ('is_readonly', '=', False), ('id', '!=', self.budget_element_src_id.id), ('user_can_modify', '=', True)]
        elif self.transfer_type == 'existing_detail':
            domains['budget_element_dst_id'] = [('budget_id.budget_id', '=', self.main_budget_dst_id.id), ('is_readonly', '=', False), ('id', '!=', self.budget_element_src_id.id), ('user_can_modify', '=', True)]

        return {'domain': domains}

    @api.onchange('transfer_type')
    def onchange_transfer_type(self):
        if self.transfer_type not in ('new_sibling', 'existing_sibling'):
            if not self.company_dst_id:
                self.company_dst_id = self.company_src_id
            else:
                self.currency_dst_id = self.main_budget_dst_id.currency_id.id
        else:
            self.currency_dst_id = self.currency_src_id.id
        return self.get_domains()

    @api.onchange('company_dst_id')
    def onchange_company_dst_id(self):
        different_company = (self.company_src_id != self.company_dst_id)
        charge = 0
        if self.company_src_id.parent_id and different_company:
            charge = -self.company_src_id.default_transfer_charge
        elif different_company:
            charge = self.company_dst_id.default_transfer_charge

        self.update({
            'main_budget_dst_id': False,
            'different_company': different_company,
            'transfer_charge': charge,
        })
        return self.get_domains()

    @api.onchange('main_budget_dst_id')
    def onchange_main_budget_dst_id(self):
        self.budget_element_dst_id = False
        self.currency_dst_id = self.main_budget_dst_id.currency_id.id
        return self.get_domains()

    @api.onchange('amount_src', 'transfer_charge', 'currency_dst_id')
    def onchange_amount(self):
        if self.currency_dst_id:
            self.amount_dst = self.currency_src_id.compute(self.amount_src * ((100.0 - self.transfer_charge) / 100.0), self.currency_dst_id)
        else:
            self.amount_dst = 0.0
        self.can_transfer = (self.amount_src > 0.0 and self.amount_src <= self.amount_available and self.amount_dst > 0.0)

    @api.model
    def default_get(self, fields_list):
        """
        Get the element ids
        """

        values = super(WizardTransferBudgetAmount, self).default_get(fields_list)

        if self.env.context.get('active_id'):
            model = self.env.context.get('active_model')
            record = self.env[model].browse(self.env.context.get('active_id'))
            if model == 'budget.element':
                values['budget_element_src_id'] = record.id
                values['currency_src_id'] = record.currency_id.id
                values['company_src_id'] = record.company_id.id
                values['transfer_type'] = 'new_line'
                values['amount_available'] = record.amount_remaining
            else:
                raise UserError(_('The model type \'%s\' is not managed.') % self.env.context.get('active_model'))

        return values

    
    def validate(self):
        self.ensure_one()
        recalc_elements = self.budget_element_src_id
        element_dst = self.budget_element_dst_id or self.budget_element_src_id
        currency_dst = (self.main_budget_dst_id or self.budget_element_src_id).currency_id
        amount_dst = self.currency_src_id.compute(self.amount_src * ((100.0 - self.transfer_charge) / 100.0), currency_dst)

        # Treat destination
        if self.transfer_type in ('new_sibling', 'new_line', 'new_detail', 'new_line_and_detail'):
            copy_params = {}
            if self.transfer_type == 'new_sibling':
                copy_params.update({
                    'amount_fixed': amount_dst,
                    'amount_initial': 0.0,
                    'profit_loss_amount_initial': 0.0,
                    'state': self.budget_element_src_id.state,
                })
            elif self.transfer_type == 'new_line':
                copy_params.update({
                    'budget_id': self.main_budget_dst_id.id,
                    'type_id': self.env.ref('advanced_budget.budget_element_type_line').id,
                    'amount_fixed': amount_dst,
                    'amount_initial': 0.0,
                    'profit_loss_amount_initial': 0.0,
                    'company_id': self.main_budget_dst_id.company_id.id,
                    'currency_id': self.main_budget_dst_id.currency_id.id,
                    'state': self.main_budget_dst_id.state,
                })
            elif self.transfer_type == 'new_detail':
                copy_params.update({
                    'budget_id': self.budget_element_dst_id.id,
                    'type_id': self.env.ref('advanced_budget.budget_element_type_detail').id,
                    'amount_fixed': amount_dst,
                    'amount_initial': 0.0,
                    'profit_loss_amount_initial': 0.0,
                    'company_id': self.main_budget_dst_id.company_id.id,
                    'currency_id': self.main_budget_dst_id.currency_id.id,
                    'state': self.main_budget_dst_id.state,
                })
            elif self.transfer_type == 'new_line_and_detail':
                copy_params.update({
                    'budget_id': self.main_budget_dst_id.id,
                    'type_id': self.env.ref('advanced_budget.budget_element_type_line').id,
                    'amount_fixed': 0.0,
                    'amount_initial': 0.0,
                    'profit_loss_amount_initial': 0.0,
                    'company_id': self.main_budget_dst_id.company_id.id,
                    'currency_id': self.main_budget_dst_id.currency_id.id,
                    'state': self.main_budget_dst_id.state,
                })
                line_src = self.budget_element_src_id
                if self.budget_element_src_id.type == 'budget_detail':  # Copy line + detail to line + detail
                    line_src = line_src.budget_id
                line = line_src.with_context({'do_not_calculate_budgets': True}).copy(copy_params)
                recalc_elements |= line
                copy_params.update({
                    'budget_id': line.id,
                    'type_id': self.env.ref('advanced_budget.budget_element_type_detail').id,
                    'amount_fixed': amount_dst,
                    'amount_initial': 0.0,
                    'profit_loss_amount_initial': 0.0,
                    'company_id': self.main_budget_dst_id.company_id.id,
                    'currency_id': self.main_budget_dst_id.currency_id.id,
                    'state': self.main_budget_dst_id.state,
                })

            element_dst = self.budget_element_src_id.with_context({'do_not_calculate_budgets': True}).copy(copy_params)

        else:  # We're modifying an existing line
            element_dst.write({
                'amount_fixed': element_dst.amount_fixed + amount_dst
            })

        # Treat source
        self.budget_element_src_id.write({
            'amount_fixed': self.budget_element_src_id.amount_fixed - self.amount_src
        })

        recalc_elements |= element_dst
        recalc_elements.calculate_amounts()
        amount_src_cur = formatLang(self.env, self.amount_src, digits=self.budget_element_src_id.currency_id.decimal_places or 0, currency_obj=self.budget_element_src_id.currency_id, grouping=True, monetary=True)
        amount_dst_cur = formatLang(self.env, amount_dst, digits=element_dst.currency_id.decimal_places or 0, currency_obj=element_dst.currency_id, grouping=True, monetary=True)
        charge_amount_src = formatLang(self.env, (self.amount_src * self.transfer_charge) / 100.0, digits=self.budget_element_src_id.currency_id.decimal_places or 0, currency_obj=self.budget_element_src_id.currency_id, grouping=True, monetary=True)
        charge_amount_dst = formatLang(self.env, amount_dst - self.currency_src_id.compute(self.amount_src, currency_dst), digits=element_dst.currency_id.decimal_places or 0, currency_obj=element_dst.currency_id, grouping=True, monetary=True)
        src_name = self.budget_element_src_id.name
        dst_name = element_dst.name
        main_budget_src = False
        main_budget_dst = False

        main_budget_src = self.budget_element_src_id
        while main_budget_src.budget_id:
            main_budget_src = main_budget_src.budget_id
            src_name = main_budget_src.name + '/' + src_name

        main_budget_dst = element_dst
        while main_budget_dst.budget_id:
            main_budget_dst = main_budget_dst.budget_id
            dst_name = main_budget_dst.name + '/' + dst_name

        # Update the main budgets' authorised amounts
        main_budget_src.write({
            'amount_fixed': main_budget_src.amount_fixed - self.amount_src
        })
        main_budget_dst.write({
            'amount_fixed': main_budget_dst.amount_fixed + amount_dst
        })

        if self.budget_element_src_id.company_id != element_dst.company_id:
            dst_name = element_dst.company_id.name + '/' + dst_name
            src_name = self.budget_element_src_id.company_id.name + '/' + src_name

        message_src = _('{amount_src} was transferred to {dst_name} from {src_name}.').format(amount_src=amount_src_cur, dst_name=dst_name, src_name=src_name)
        message_dst = _('{amount_dst} was received from {src_name} to {dst_name}.').format(amount_dst=amount_dst_cur, src_name=src_name, dst_name=dst_name)
        if self.transfer_charge != 0:
            message_src += _(' A transfer charge of {charge} % ({charge_amount}) was applied').format(charge=self.transfer_charge, charge_amount=charge_amount_src)
            message_dst += _(' A transfer charge of {charge} % ({charge_amount}) was applied').format(charge=self.transfer_charge, charge_amount=charge_amount_dst)
            if element_dst.currency_id == self.budget_element_src_id.currency_id:
                message_src += _(', making a total credit of {amount_dst}').format(amount_dst=amount_dst_cur)
                message_dst += _(', making a total debit of {amount_src}').format(amount_src=amount_src_cur)
            else:
                message_src += '.'
                message_dst += '.'

        if element_dst.currency_id != self.budget_element_src_id.currency_id:
            equivalent = self.currency_src_id.compute(1, currency_dst, round=False)
            exchange = _('{from_one} = {to_one}').format(from_one=formatLang(self.env, 1.0, digits=6, currency_obj=self.budget_element_src_id.currency_id, grouping=True, monetary=True),
                                                         to_one=formatLang(self.env, equivalent, digits=6, currency_obj=element_dst.currency_id, grouping=True, monetary=True))
            message_src += ' ' + _('With the exchange rate of {exchange}, a total of {amount_dst} was credited.').format(exchange=exchange, amount_dst=amount_dst_cur)
            equivalent = currency_dst.compute(1, self.currency_src_id, round=False)
            exchange = _('{from_one} = {to_one}').format(from_one=formatLang(self.env, 1.0, digits=6, currency_obj=element_dst.currency_id, grouping=True, monetary=True),
                                                         to_one=formatLang(self.env, equivalent, digits=6, currency_obj=self.budget_element_src_id.currency_id, grouping=True, monetary=True))
            message_dst += ' ' + _('With the exchange rate of {exchange}, a total of {amount_src} was debited.').format(exchange=exchange, amount_src=amount_src_cur)

        # formatLang returns double-spaces between the amounts and the currencies
        message_src = message_src.replace('  ', ' ')
        message_dst = message_dst.replace('  ', ' ')

        self.budget_element_src_id.message_post(body=message_src)
        element_dst.message_post(body=message_dst)
        main_budget_src.message_post(body=message_src)
        main_budget_dst.message_post(body=message_dst)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
