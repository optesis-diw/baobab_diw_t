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

from odoo import models, api, fields, exceptions


class WizardViewBudgetDataPurchaseLine(models.TransientModel):
    _name = 'wizard.view.budget.data.purchase.line'
    _description = 'View Budget Data Purchase Line'

    wizard_id = fields.Many2one(comodel_name='wizard.view.budget.data', string='Wizard')
    # order_id = fields.Many2one(comodel_name='purchase.order', string='Purchase Order', help='The purchase order.')
    order_name = fields.Char(string='Order',  help='The purchase order.')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner', help='The partner.')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('to approve', 'Budgetary validation'),
        ('to approve twice', 'Head validation'),
        ('purchase', 'Ongoing'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='budget Status')
    date_planned = fields.Date(string='Scheduled Date', help='The scheduled date.')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', help='The product.')
    name = fields.Text(string='Description', help='The description of the purchase.')
    amount = fields.Monetary(string='Amount Currency', currency_field='currency_id')
    amount_currency = fields.Monetary(string='Amount Untaxed', currency_field='company_currency_id')
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags30', help='This contains the axis tags for this purchase line.')
    text_distribution = fields.Char(string='Distribution', size=128, help='The distribution.')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency')
    company_currency_id = fields.Many2one(comodel_name='res.currency', string='Company\'s Currency', help='The currency')


class WizardViewBudgetDataMoveLineLine(models.TransientModel):
    _name = 'wizard.view.budget.data.move_line.line'
    _description = 'View Budget Data Move Line Line'

    wizard_id = fields.Many2one(comodel_name='wizard.view.budget.data', string='Wizard')
    move_id = fields.Many2one(comodel_name='account.move', string='Journal Entry', help='The journal entry.')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner', help='The partner.')
    date = fields.Date(string='Scheduled Date', help='The journal item\'s date.')
    name = fields.Char(string='Label', help='The description of the journal item.')
    balance = fields.Monetary(string='Amount Untaxed', currency_field='company_currency_id')
    amount_currency = fields.Monetary(string='Amount Currency', currency_field='currency_id')
    invoice_state = fields.Selection(selection=[('na', 'N/A'), ('paid', 'Paid'), ('not_paid', 'Not paid')], string='Invoice state',
                                     help='The status of the invoice linked to this journal item.')
    ref = fields.Char(string='Partner ref', help='The reference of the journal item.')
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags31', help='This contains the axis tags for this purchase line.')
    text_distribution = fields.Char(string='Distribution', size=128, help='The distribution.')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency.')
    company_currency_id = fields.Many2one(comodel_name='res.currency', string='Company\'s Currency', help='The currency')


class WizardViewBudgetDataAssetLine(models.TransientModel):
    _name = 'wizard.view.budget.data.asset.line'
    _description = 'View Budget Data asset Line'

    wizard_id = fields.Many2one(comodel_name='wizard.view.budget.data', string='Wizard')
    name = fields.Char(string='Description', help='The description of the asset.')
    category_id = fields.Many2one(comodel_name='account.asset', string='Category', help='The category.')
    date = fields.Date(string='Scheduled Date', help='The scheduled date.')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner', help='The partner.')
    value = fields.Monetary(string='Gross value', currency_field='currency_id')
    value_residual = fields.Monetary(string='Residual value', currency_field='currency_id')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency.')
    state = fields.Selection([('draft', 'Draft'), ('open', 'Running'), ('close', 'Close')], string='Status')
    is_accrued_expense = fields.Boolean(string='Is accrued expense')
    asset_id = fields.Many2one(comodel_name='account.asset', string='Asset', help='The asset')


class WizardViewBudgetData(models.TransientModel):
    _name = "wizard.view.budget.data"
    _description = "View Budget Data Wizard"

    budget_element_id = fields.Many2one(comodel_name='budget.element', string='Budget element', help='The budget element')
    view_type = fields.Selection(selection=[
        ('purchase', 'Purchases'),
        ('journal', 'Journal'),
        ('asset', 'Assets')
    ], string='View type', default='purchase')
    purchase_line_ids = fields.One2many(comodel_name='wizard.view.budget.data.purchase.line', inverse_name='wizard_id', string='Purchase lines')
    move_line_ids = fields.One2many(comodel_name='wizard.view.budget.data.move_line.line', inverse_name='wizard_id', string='Journal items')
    amortisation_ids = fields.One2many(comodel_name='wizard.view.budget.data.asset.line', inverse_name='wizard_id', string='Amortisations', domain=[('is_accrued_expense', '=', False)])
    accrued_expense_ids = fields.One2many(comodel_name='wizard.view.budget.data.asset.line', inverse_name='wizard_id', string='Accrued Expenses', domain=[('is_accrued_expense', '=', True)])

    @api.model
    def default_get(self, fields_list):
        """
        Return budget element information
        """
        values = super(WizardViewBudgetData, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'budget.element' and self.env.context.get('active_id'):
            budget_element = self.env['budget.element'].browse(self.env.context.get('active_id'))
            element_ids = budget_element.mapped('budget_line_ids.budget_detail_ids.id') + budget_element.mapped('budget_line_ids.id') + budget_element.mapped('budget_detail_ids.id') + budget_element.mapped('id')
            values['budget_element_id'] = budget_element.id
            if self._context.get('data_type'):
                values['view_type'] = self._context['data_type']
            if values['view_type'] == 'purchase':
                purchase_lines = []
                lines = self.env['purchase.order.line'].sudo().search([('budget_element_id', 'in', element_ids)])
                for line in lines:
                    order = line.sudo().order_id
                    current_rate = order.currency_id.with_context({'company_id': budget_element.company_id.id, 'date': order.date_order}).rate or 1.0
                    subtotal = line.price_subtotal
                    currency_id = line.currency_id.id
                    if order.company_id.currency_id == line.currency_id:
                        subtotal = False
                        currency_id = False

                    purchase_lines.append((0, 0, {
                        'order_name': order.name,
                        'partner_id': order.partner_id.id,
                        'state': order.microcred_state,
                        'date_planned': line.date_planned,
                        'name': line.name,
                        'amount': subtotal,
                        'amount_currency': order.company_id.currency_id.round(line.price_subtotal / current_rate),
                        'all_tag_ids': [(6, 0, [t.id for t in line.all_tag_ids])],
                        'text_distribution': line.text_distribution,
                        'currency_id': currency_id,
                        'company_currency_id': order.company_id.currency_id.id,
                    }))

                values['purchase_line_ids'] = purchase_lines

            elif values['view_type'] == 'journal':
                move_lines = []
                lines = self.env['account.move.line'].sudo().search([('budget_element_id', 'in', element_ids), ('move_id.asset_id', '=', False)])
                for line in lines:
                    move_lines.append((0, 0, {
                        'move_id': line.move_id.id,
                        'partner_id': line.partner_id.id,
                        'date': line.date,
                        'name': line.name,
                        'balance': line.balance,
                        'amount_currency': line.amount_currency,
                        'invoice_state': line.invoice_state,
                        'ref': line.ref,
                        'all_tag_ids': [(6, 0, [t.id for t in line.all_tag_ids])],
                        'text_distribution': line.text_distribution,
                        'currency_id': line.currency_id.id,
                        'company_currency_id': line.company_currency_id.id,
                    }))

                values['move_line_ids'] = move_lines

            elif values['view_type'] == 'asset':
                amort_lines = []
                accrued_lines = []
                assets = self.env['account.asset'].sudo().search([('budget_element_id', 'in', element_ids)]).mapped('asset_id')
                for asset in assets:
                    data = (0, 0, {
                        'name': asset.name,
                        'category_id': asset.category_id.id,
                        'date': asset.date,
                        'partner_id': asset.partner_id.id,
                        'value': asset.value,
                        'value_residual': asset.value_residual,
                        'currency_id': asset.currency_id.id,
                        'state': asset.state,
                        'is_accrued_expense': asset.is_accrued_expense,
                        'asset_id': asset.id
                    })
                    if asset.is_accrued_expense:
                        accrued_lines.append(data)
                    else:
                        amort_lines.append(data)

                values['amortisation_ids'] = amort_lines
                values['accrued_expense_ids'] = accrued_lines

        return values

    
    def open_assets(self):
        self.ensure_one()
        asset_ids = [x.asset_id.id for x in self.amortisation_ids]
        action = self.env.ref('account_asset.action_account_asset_asset_form', False)
        action_data = action.read()[0]

        action_data.update(
            domain=[('id', 'in', asset_ids)],
            context={
                'target': 'new',
            },
            # target='new'
        )
        if len(asset_ids) == 1:
            action_data.update({
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': asset_ids[0],
                'views': [(self.env.ref('microcred_profile.view_account_asset_asset_form').id, 'form')],
            })
        return action_data

    
    def open_accrued_expenses(self):
        self.ensure_one()
        asset_ids = [x.asset_id.id for x in self.accrued_expense_ids]
        action = self.env.ref('microcred_profile.action_account_asset_accrued_expense_form', False)
        action_data = action.read()[0]

        action_data.update(
            domain=[('id', 'in', asset_ids)],
            context={
                'target': 'new',
            },
            # target='new'
        )
        if len(asset_ids) == 1:
            action_data.update({
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': asset_ids[0],
                'views': [(self.env.ref('microcred_profile.view_account_asset_accrued_expense_form').id, 'form')],
            })
        return action_data


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
