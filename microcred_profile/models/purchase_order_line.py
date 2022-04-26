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

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    #tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string=' Axis tags', deprecated=True, help='This contains the axis tags for this purchase line.')
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags15', help='This contains the axis tags for this purchase line.')
    text_distribution = fields.Char(string='Distribution', size=128, help='The distribution.', compute='_get_text_distribution', )
    budget_element_id = fields.Many2one(index=True)

    
    def add_follower_to_purchase_order(self):
        def safe_subscribe(line, partner_id):
            if partner_id and partner_id != line.order_id.create_uid.partner_id:  # Create users are automatically subscribed - we can't add them a second time ((his is done by Odoo standard)
                line.sudo().order_id.message_subscribe(partner_ids=[partner_id.id])

        for line in self:
            if line.budget_element_id:
                main_budget = False
                if line.budget_element_id.type == 'budget_line':
                    main_budget = line.budget_element_id.budget_id
                elif line.budget_element_id.type == 'budget_detail':
                    main_budget = line.budget_element_id.budget_id.budget_id
                if main_budget:
                    safe_subscribe(line, main_budget.sudo().user_id.partner_id)
                    if main_budget.budget_department_id:
                        safe_subscribe(line, main_budget.sudo().budget_department_id.user_id.partner_id)
                for partner in line.budget_element_id.mapped('message_follower_ids.partner_id'):
                    safe_subscribe(line, partner)

    
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
                        'purchase_line_id': line.id,
                        'parent_id': False,
                    })

            # Get best tags
            element = line.budget_element_id
            self.invalidate_cache()  # Wierd things happen if the cache isn't invalidated (element.all_tag_ids return a recordset of budget.element and not account.axis.tag...)
            while not element.all_tag_ids and element:
                element = element.budget_id

            if element:
                tags = [(5, 0, 0)]
                for tag in element.all_tag_ids:
                    tags.append((4, tag.id))
                line.all_tag_ids = tags


    def _prepare_invoice(self, budget_element_id=None):
        
        invoice_vals = {
            'budget_element_id': budget_element_id,
        }
        return invoice_vals

    @api.model
    def create(self, vals):
        """
        Copy the axes and the budget element distributions
        """
        new_line = super(PurchaseOrderLine, self).create(vals)

        if vals.get('budget_element_id', False):
            #new_line.check_asset_type()
            if new_line.budget_element_id.company_id != new_line.order_id.company_id:
                raise UserError(_('Purchase orders and budget elements must belong to the same company.'))
            new_line.copy_budget_distribution()
            new_line.sudo().add_follower_to_purchase_order()  # Sudo required for subscribing users for budgets for which we don't necessarily have access
            new_line.budget_element_id.calculate_amounts()

        return new_line

    
    def write(self, vals):
        """
        Copy the axes and the budget element distributions
        """
        recalc_budgets = self.env['budget.element']
        if 'budget_element_id' in vals:
            # Since we're manually handling budget calculation, we need to recalculate old budgets
            recalc_budgets |= self.filtered(lambda r: r.budget_element_id is not False).mapped('budget_element_id')

        ret = super(PurchaseOrderLine, self).write(vals)

       # self.check_asset_type()
        if vals.get('budget_element_id', False):
            for line in self:
                if line.budget_element_id.company_id != line.order_id.company_id:
                    raise UserError(_('Purchase orders and budget elements must belong to the same company.'))
            self.copy_budget_distribution()
            self.sudo().add_follower_to_purchase_order()  # Sudo required for subscribing users for budgets for which we don't necessarily have access

        if 'budget_element_id' in vals or \
           'price_unit' in vals or \
           'product_qty' in vals or \
           'price_subtotal' in vals:
            recalc_budgets |= self.filtered(lambda r: r.budget_element_id is not False).mapped('budget_element_id')

        if recalc_budgets:
            recalc_budgets.calculate_amounts()

        if 'all_tag_ids' in vals:
            self.mapped('order_id').set_axis_fields()

        return ret
    
    
    
    def _prepare_invoice(self):
        
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')
       
        
        journal = self.env['account.move'].with_context(default_move_type=move_type)._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting purchase journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        partner_invoice_id = self.partner_id.address_get(['invoice'])['invoice']
        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'invoice_user_id': self.user_id and self.user_id.id or self.env.user.id,
            'partner_id': partner_invoice_id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(partner_invoice_id)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': self.partner_id.bank_ids[:1].id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'budget_element_id':self.budget_element_id,
            'all_tag_ids':self.all_tag_ids,
           
           
            
        }
        return invoice_vals

    
   
    
    def unlink(self):
        """
        Recalculate budgets from deleted lines
        """
        recalc_budgets = self.filtered(lambda r: r.budget_element_id is not False).mapped('budget_element_id')
        ret = super(PurchaseOrderLine, self).unlink()
        recalc_budgets.calculate_amounts()
        return ret

    
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
                    distributions.append(_('%s: %.2f%% (%.2f)') % (distribution.child_id.name, distribution.percentage, distribution.amount_fixed or distribution.amount_calculated))

            if distributions:
                line.text_distribution = ', '.join(distributions)
            else:
                line.text_distribution = _("None")

    @api.model
    def default_get(self, fields_list):
        """
        Get default product
        """
        values = super(PurchaseOrderLine, self).default_get(fields_list)

        if 'product_id' in fields_list and 'product_id' not in values:
            values['product_id'] = self.env.user.company_id.default_expensify_product_id.id

        return values


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
