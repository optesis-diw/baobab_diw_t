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

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare


class BudgetElementDistribution(models.Model):
    _name = 'budget.element.distribution'
    _description = 'Budget element distribution'

    parent_id = fields.Many2one('budget.element', string='Parent', help='Parent budget element', required=False, )
    purchase_id = fields.Many2one('purchase.order', string='Purchase order')
    sale_id = fields.Many2one('sale.order', string='Sale order')
    move_id = fields.Many2one('account.move', string='Invoice order')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase line')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice line')
    child_id = fields.Many2one('budget.element', string='Child', help='Child budget element', required=True, )
    amount_fixed = fields.Float(string='Fixed amount', digits=(100,2), help='Enter the fixed amount.')
    percentage = fields.Float(string='Percentage', digits=(100,2), help='Enter the percentage (if there is no fixed amount).')
    equivalent_percentage = fields.Float(string='equivalent Percentage', digits=(100,2), compute='_get_equivalent_percentage', )  # This contains the equivalent percentage for fixed amounts
    amount_calculated = fields.Float(string='Calculated amount', digits=(100,2), help='Enter the calculated amount.', compute='_get_calculated_amount', )
    amount_engaged = fields.Float(string='Engaged amount', digits=(100,2), help='The engaged amount.', compute='_get_engaged_amount', )
    amount_invoiced = fields.Float(string='invoice amount', digits=(100,2), help='The engaged amount.', compute='_get_invoiced_amount', )
    type = fields.Selection([('cost', 'Cost'), ('budget', 'Budget')], string='budget Type', compute='_get_type', store=True, )
    linked_budget_line_ids = fields.One2many('budget.element', 'linked_distribution_id', string='Linked budget lines')

    
    @api.depends('child_id')
    def _get_type(self):
        for distribution in self:
            if distribution.child_id.type in ('periodic', 'project'):
                distribution.type = 'budget'
            else:
                distribution.type = 'cost'

    
    def _get_equivalent_percentage(self):
        for distribution in self:
            if distribution.percentage:
                distribution.equivalent_percentage = distribution.percentage
            else:
                total_amount = 0.0
                if distribution.parent_id:
                    for sibling in distribution.parent_id.distribution_budget_ids:
                        total_amount += sibling.amount_calculated
                elif distribution.purchase_id:
                    for sibling in distribution.purchase_id.distribution_cost_ids:
                        total_amount += sibling.amount_calculated
                elif distribution.purchase_line_id:
                    for sibling in distribution.purchase_line_id.distribution_cost_ids:
                        total_amount += sibling.amount_calculated
                elif distribution.sale_id:
                    for sibling in distribution.sale_id.distribution_cost_ids:
                        total_amount += sibling.amount_calculated
                elif distribution.sale_line_id:
                    for sibling in distribution.sale_line_id.distribution_cost_ids:
                        total_amount += sibling.amount_calculated
                elif distribution.move_id:
                    for sibling in distribution.move_id.distribution_cost_ids:
                        total_amount += sibling.amount_calculated
                elif distribution.invoice_line_id:
                    for sibling in distribution.invoice_line_id.distribution_cost_ids:
                        total_amount += sibling.amount_calculated

                distribution.equivalent_percentage = (total_amount and (distribution.amount_fixed * 100.0) / total_amount) or 0.0

    def _get_engaged_amount(self):
        """
        Calculate the engaged amount
        """
        for distribution in self:
            distribution.amount_engaged = (distribution.parent_id.amount_engaged * distribution.equivalent_percentage) / 100.0

    def _get_invoiced_amount(self):
        """
        Calculate the invoiced amount
        """
        for distribution in self:
            distribution.amount_invoiced = (distribution.parent_id.amount_invoiced * distribution.equivalent_percentage) / 100.0

    
    def _check_percentage_and_fixed(self):
        for distribution in self:
            if distribution.amount_fixed and distribution.percentage:
                return False

        return True

    constraints = [
        (_check_percentage_and_fixed, 'Error: You cannot define both a fixed amount and a percentage.', ['amount_fixed', 'percentage']),
    ]

    
    def _get_calculated_amount(self):
        for distribution in self:
            if distribution.parent_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.parent_id.amount_calculated / 100.0)
            elif distribution.move_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.move_id.amount_untaxed / 100.0)
            elif distribution.invoice_line_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.invoice_line_id.price_subtotal / 100.0)
            elif distribution.purchase_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.purchase_id.amount_untaxed / 100.0)
            elif distribution.purchase_line_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.purchase_line_id.price_subtotal / 100.0)
            elif distribution.sale_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.sale_id.amount_untaxed / 100.0)
            elif distribution.sale_line_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.sale_line_id.price_subtotal / 100.0)

    @api.onchange('amount_fixed', 'percentage')
    def onchange_percentage_or_fixed(self):
        if self.percentage and self.amount_fixed:
            return {
                'warning': {
                    'title': 'Error',
                    'message': 'You cannot define both a fixed amount and a percentage.',
                }
            }

    
    def _make_budget_line_dico(self):
        self.ensure_one()

        return {
            'linked_distribution_id': self.id,
            'is_readonly': True,
            'name': self.parent_id.name,
            'type_id': self.env.ref('advanced_budget.budget_element_type_line').id,
            'amount_fixed': self.amount_calculated,
            'budget_id': self.child_id.id,
        }

    
    def create_budget_lines(self):
        budget_element_obj = self.env['budget.element']
        for distribution in self:
            budget_element_obj.create(distribution._make_budget_line_dico())

    @api.model
    def create(self, vals):
        new_distribution = super(BudgetElementDistribution, self).create(vals)

        if new_distribution.child_id.type in ('periodic', 'project'):
            new_distribution.create_budget_lines()

        return new_distribution

    
    def write(self, vals):
        if 'child_id' in vals:
            self.filtered('parent_id').mapped('linked_budget_line_ids').with_context({'allow_readonly': True}).unlink()

        ret = super(BudgetElementDistribution, self).write(vals)

        if 'child_id' in vals:
            for distribution in self:
                if distribution.parent_id:
                    # distribution.linked_budget_line_ids.unlink()  # Delete all former linked budget lines
                    distribution.create_budget_lines()  # And create new ones
        elif 'amount_fixed' or 'percentage' in vals:  # If we've done the child_id, there's no need to do these two fields
            for element in self.mapped('linked_budget_line_ids'):
                new_amount = element.linked_distribution_id.amount_fixed or element.linked_distribution_id.amount_calculated
                if float_compare(element.amount_fixed, new_amount, precision_digits=2):
                    element.write({'amount_fixed': new_amount})

        return ret

    
    def unlink(self):
        """
        Remove all linked budget lines
        """
        self.with_context(allow_readonly=True).mapped('linked_budget_line_ids').unlink()
        super(BudgetElementDistribution, self).unlink()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
