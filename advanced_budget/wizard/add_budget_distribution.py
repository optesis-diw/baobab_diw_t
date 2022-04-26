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

from odoo import models, api, fields
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import _
from time import sleep


class WizardAddBudgetDistributionLine(models.TransientModel):
    _name = "wizard.add.budget.distribution.line"
    _description = "Add budget distribution line"

    child_id = fields.Many2one('budget.element', string='Child', help='Child budget element', required=True, )
    amount_fixed = fields.Float(string='Fixed amount', digits=(100,2), help='Enter the fixed amount.')
    percentage = fields.Float(string='budget Percentage', digits=(100,2), help='Enter the percentage (if there is no fixed amount).')
    amount_calculated = fields.Float(string='Calculated amount', digits=(100,2), help='Enter the calculated amount.', compute='_get_calculated_amount', )
    amount_parent = fields.Float(string='Parent\'s amount', digits=(100,2), related='wizard_id.amount')
    wizard_id = fields.Many2one('wizard.add.budget.distribution', string='Wizard')
    distribution_id = fields.Many2one('budget.element.distribution', string='Distribution')

    
    def _check_individual_percentage_and_fixed(self):
        if self.amount_fixed and self.percentage:
            return False
        return True

    
    @api.constrains('amount_fixed', 'percentage')
    def _check_percentage_and_fixed(self):
        for distribution in self:
            if not distribution._check_individual_percentage_and_fixed():
                return False

        return True

    
    def _get_calculated_amount(self):
        for distribution in self:
            distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.amount_parent / 100.0)

    @api.onchange('amount_fixed', 'percentage')
    def onchange_percentage_or_fixed(self):
        self.amount_calculated = self.amount_fixed or (self.percentage * self.amount_parent / 100.0)
        if not self._check_individual_percentage_and_fixed():
            return {
                'warning': {
                    'title': 'Error',
                    'message': 'You cannot define both a fixed amount and a percentage.',
                }
            }


class WizardAddBudgetDistribution(models.TransientModel):
    _name = "wizard.add.budget.distribution"
    _description = "Add budget distribution wizard"

    element_id = fields.Many2one('budget.element', string='Budget line', readonly=True, )
    purchase_id = fields.Many2one('purchase.order', string='Purchase order', readonly=True, )
    sale_id = fields.Many2one('sale.order', string='Sale order', readonly=True, )
    move_id = fields.Many2one('account.move', string='Invoice order', readonly=True, )
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase line', readonly=True, )
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', readonly=True, )
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice line', readonly=True, )
    amount = fields.Float(string='Amount', digits=(100,2), help='The planned amount.', readonly=True, )
    is_ok = fields.Char(string='Is Ok', size=128, readonly=True, )
    line_ids = fields.One2many('wizard.add.budget.distribution.line', 'wizard_id', string='Budget distributions', help='Add budget distributions.')
    copy_from_selection = fields.Selection([
        ('budget_element', 'Budget element'),
        ('purchase', 'Purchase order'),
        ('purchase_line', 'Purchase order line'),
        ('invoice', 'Invoice or refund'),
        ('invoice_line', 'Invoice or refund line'),
        ('sale', 'Sale order'),
        ('sale_line', 'Sale order line'),
    ], string='Copy from', help='Select from where you want to copy this distribution.')
    copy_from_budget_id = fields.Many2one('budget.element', string='Copy from budget element', help='Select a budget element from which the distribution is to be copied from.')
    copy_from_purchase_id = fields.Many2one('purchase.order', string='Copy from purchase order', help='Select a purchase order from which the distribution is to be copied from.')
    copy_from_purchase_line_id = fields.Many2one('purchase.order.line', string='Copy from purchase order line', help='Select a purchase order line from which the distribution is to be copied from.')
    copy_from_move_id = fields.Many2one('account.move', string='Copy from invoice', help='Select an invoice from which the distribution is to be copied from.')
    copy_from_invoice_line_id = fields.Many2one('account.move.line', string='Copy from invoice line', help='Select an invoice line from which the distribution is to be copied from.')
    copy_from_sale_id = fields.Many2one('sale.order', string='Copy from sale order', help='Select a sale order from which the distribution is to be copied from.')
    copy_from_sale_line_id = fields.Many2one('sale.order.line', string='Copy from sale order line', help='Select a sale order line from which the distribution is to be copied from.')

    @api.model
    def default_get(self, fields_list):
        """
        Return budget line information
        """

        values = super(WizardAddBudgetDistribution, self).default_get(fields_list)

        distributions = []
        element = False
        element_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'budget.element':
            values['element_id'] = self.env.context.get('active_id')
            element = self.env['budget.element'].browse(element_id)
            values['amount'] = element.amount_calculated
        elif self.env.context.get('active_model') == 'sale.order.line':
            values['sale_line_id'] = self.env.context.get('active_id')
            element = self.env['sale.order.line'].browse(element_id)
            values['amount'] = element.price_subtotal
        elif self.env.context.get('active_model') == 'purchase.order.line':
            values['purchase_line_id'] = self.env.context.get('active_id')
            element = self.env['purchase.order.line'].browse(element_id)
            values['amount'] = element.price_subtotal
        elif self.env.context.get('active_model') == 'account.move.line':
            values['invoice_line_id'] = self.env.context.get('active_id')
            element = self.env['account.move.line'].browse(element_id)
            values['amount'] = element.price_subtotal

        if element:
            for distribution in element.distribution_cost_ids:
                distributions.append(
                    [0, 0, {
                        'child_id': distribution.child_id.id,
                        'amount_fixed': distribution.amount_fixed,
                        'percentage': distribution.percentage,
                        'amount_calculated': distribution.amount_fixed or (distribution.percentage * values['amount'] / 100.0),
                        'distribution_id': distribution.id,
                    }]
                )

        if distributions:
            values['line_ids'] = distributions

        return values

    def create_new_lines(self, model):
        new_lines = [(5, 0, 0)]
        for distribution in model.distribution_cost_ids:
            new_lines.append(
                [0, 0, {
                    'child_id': distribution.child_id.id,
                    'amount_fixed': distribution.amount_fixed,
                    'percentage': distribution.percentage,
                    'amount_calculated': distribution.amount_fixed or (distribution.percentage * self.amount / 100.0)
                }]
            )

        return new_lines

    @api.onchange('copy_from_selection')
    def copy_from(self):
        # Clear the ids
        self.copy_from_budget_id = False
        self.copy_from_move_id = False
        self.copy_from_invoice_line_id = False
        self.copy_from_purchase_id = False
        self.copy_from_purchase_line_id = False
        self.copy_from_sale_id = False
        self.copy_from_sale_line_id = False

    @api.onchange('copy_from_budget_id')
    def copy_from_budget(self):
        self.ensure_one()
        if self.copy_from_budget_id:
            self.line_ids = self.create_new_lines(self.copy_from_budget_id)

    @api.onchange('copy_from_move_id')
    def copy_from_invoice(self):
        self.ensure_one()
        if self.copy_from_move_id:
            self.line_ids = self.create_new_lines(self.copy_from_move_id)

    @api.onchange('copy_from_invoice_line_id')
    def copy_from_invoice_line(self):
        self.ensure_one()
        if self.copy_from_invoice_line_id:
            self.line_ids = self.create_new_lines(self.copy_from_invoice_line_id)

    @api.onchange('copy_from_purchase_id')
    def copy_from_purchase(self):
        self.ensure_one()
        if self.copy_from_purchase_id:
            self.line_ids = self.create_new_lines(self.copy_from_purchase_id)

    @api.onchange('copy_from_purchase_line_id')
    def copy_from_puirchase_line(self):
        self.ensure_one()
        if self.copy_from_purchase_line_id:
            self.line_ids = self.create_new_lines(self.copy_from_purchase_line_id)

    @api.onchange('copy_from_sale_id')
    def copy_from_sale(self):
        self.ensure_one()
        if self.copy_from_sale_id:
            self.line_ids = self.create_new_lines(self.copy_from_sale_id)

    @api.onchange('copy_from_sale_line_id')
    def copy_from_sale_line(self):
        self.ensure_one()
        if self.copy_from_sale_line_id:
            self.line_ids = self.create_new_lines(self.copy_from_sale_line_id)

    @api.onchange('line_ids')
    def check_total_amount(self):
        for wizard in self:
            total = 0.0
            for line in wizard.line_ids:
                total += line.amount_fixed or (line.percentage * wizard.amount / 100.0)

            if round(total, 2) != round(wizard.amount, 2):
                wizard.is_ok = _('The total distribution is not equal to that of the amount.')
            else:
                wizard.is_ok = False

    
    def validate(self, this_element=None):
        """
        Validate the details
        """
        distribution_obj = self.env['budget.element.distribution']

        for wizard in self:
            element = False
            extra_field = ''
            if wizard.element_id:
                element = wizard.element_id
            elif wizard.purchase_line_id:
                element = wizard.purchase_line_id
            elif wizard.invoice_line_id:
                element = wizard.invoice_line_id
            elif this_element:
                element = this_element[0]
                extra_field = this_element[1]

            distributions_to_delete = element.distribution_cost_ids - wizard.filtered('line_ids.distribution_id').mapped('line_ids.distribution_id')
            if distributions_to_delete:
                distributions_to_delete.unlink()

            if element:
                # element.distribution_cost_ids.unlink()
                for distribution in wizard.line_ids:
                    if distribution.distribution_id:
                        distribution.distribution_id.write({
                            'child_id': distribution.child_id.id,
                            'amount_fixed': distribution.amount_fixed,
                            'percentage': distribution.percentage,
                        })
                    else:
                        new_vals = {
                            'parent_id': wizard.element_id.id,
                            'purchase_id': wizard.purchase_id.id,
                            'sale_id': wizard.sale_id.id,
                            'move_id': wizard.move_id.id,
                            'purchase_line_id': wizard.purchase_line_id.id,
                            'sale_line_id': wizard.sale_line_id.id,
                            'invoice_line_id': wizard.invoice_line_id.id,
                            'child_id': distribution.child_id.id,
                            'amount_fixed': distribution.amount_fixed,
                            'percentage': distribution.percentage,
                        }
                        if extra_field:
                            new_vals[extra_field] = element.id
                        distribution_obj.create(new_vals)

        sleep(0.5)  # There appears to be a problem where the ORM finishes but not the database - this problem is solved by the sleep (it happens especially when the user validates multiple distributions on long invoices)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
