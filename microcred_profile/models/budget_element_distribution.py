# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Microcred profile
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

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
import logging
logger = logging.getLogger('microcred_profile')


class BudgetElementDistribution(models.Model):
    _inherit = 'budget.element.distribution'

    amount_calculated = fields.Float(compute='_get_calculated_amount', )
    move_line_id = fields.Many2one('account.move.line', string='Move Line')
    asset_line_id = fields.Many2one('account.asset', string='Asset line')
    statement_line_id = fields.Many2one(comodel_name='account.bank.statement.line', string='Statement line')
    amount_invoiced = fields.Float(string='Invoiced amount', digits=("Account"), help='The invoiced amount.', compute=False)
    amount_engaged = fields.Float(string='Engaged amount', digits=("Account"), help='The engaged amount.', compute=False)
    profit_loss_amount_invoiced = fields.Float(string='P&L Invoiced amount', digits=("Account"), help='The P&L invoiced amount.', compute=False)
    profit_loss_amount_engaged = fields.Float(string='P&L Engaged amount', digits=("Account"), help='The P&L engaged amount.', compute=False)
    profit_loss_amount_fixed = fields.Float(string='P&L forecasted amount', digits=("Account"), help='The P&L fixed amount.', compute=False)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help='The currency', related='parent_id.company_id.currency_id', readonly=True)

    
    def _get_calculated_amount(self):
        for distribution in self:
            if distribution.parent_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * (distribution.parent_id.amount_fixed or distribution.parent_id.amount_calculated) / 100.0)
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
            elif distribution.asset_line_id:
                distribution.amount_calculated = distribution.amount_fixed or (distribution.percentage * distribution.asset_line_id.depreciation_value / 100.0)

    @api.depends(
        # Itself
        'move_line_id.credit',
        'move_line_id.debit',
        'move_line_id.budget_element_id',
        # Parent
        'parent_id',
        'parent_id.move_line_ids.credit',
        'parent_id.move_line_ids.debit',
        'parent_id.move_line_ids.budget_element_id',
        # Budget lines of the parent
        'parent_id.budget_line_ids',
        'parent_id.budget_line_ids.amount_invoiced',
        'parent_id.budget_line_ids.move_line_ids.credit',
        'parent_id.budget_line_ids.move_line_ids.debit',
        'parent_id.budget_line_ids.move_line_ids.budget_element_id',
        # Budget details of the parent
        'parent_id.budget_detail_ids',
        'parent_id.budget_detail_ids.amount_invoiced',
        'parent_id.budget_detail_ids.move_line_ids.credit',
        'parent_id.budget_detail_ids.move_line_ids.debit',
        'parent_id.budget_detail_ids.move_line_ids.budget_element_id',
        # Budget details of budget lines of the parent
        'parent_id.budget_line_ids.budget_detail_ids',
        'parent_id.budget_line_ids.budget_detail_ids.amount_invoiced',
        'parent_id.budget_line_ids.budget_detail_ids.move_line_ids.credit',
        'parent_id.budget_line_ids.budget_detail_ids.move_line_ids.debit',
        'parent_id.budget_line_ids.budget_detail_ids.move_line_ids.budget_element_id',
        # Linked distributions of the parent
        'parent_id.linked_distribution_id',
        'parent_id.linked_distribution_id.amount_invoiced',
    )
    def _get_invoiced_amount(self):
        """
        Calculate the invoiced amount
        """
        for distribution in self:
            distribution.amount_invoiced = (distribution.parent_id.amount_invoiced * distribution.equivalent_percentage) / 100.0
            distribution.parent_id.calculate_amounts()

    
    def calculate_amounts(self):
        # logger.info(u'Started budget_element_distribution calculate_amounts %s', repr(self.ids))
        for distribution in self:
            distribution.write({
                'amount_engaged': (distribution.parent_id.amount_engaged * distribution.equivalent_percentage / 100.0),
                'amount_invoiced': (distribution.parent_id.amount_invoiced * distribution.equivalent_percentage / 100.0),
                'profit_loss_amount_fixed': (distribution.parent_id.profit_loss_amount_fixed * distribution.equivalent_percentage / 100.0),
                'profit_loss_amount_engaged': (distribution.parent_id.profit_loss_amount_engaged * distribution.equivalent_percentage / 100.0),
                'profit_loss_amount_invoiced': (distribution.parent_id.profit_loss_amount_invoiced * distribution.equivalent_percentage / 100.0)
            })
        self.mapped('linked_budget_line_ids').calculate_amounts()
        # logger.info(u'Ended budget_element_distribution calculate_amounts %s', repr(self.ids))

    
    def _make_budget_line_dico(self):
        self.ensure_one()

        ret = super(BudgetElementDistribution, self)._make_budget_line_dico()

        ret.update({
            'budget_line_type_id': self.parent_id.budget_line_type_id.id,
            'subtype_id': self.parent_id.subtype_id.id,
            'all_tag_ids': [(6, 0, [x.id for x in self.parent_id.all_tag_ids])],
        })

        return ret


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
