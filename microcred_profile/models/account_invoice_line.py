# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
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

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'
    _name ='account.move.line'

    reinvoice_distribution_id = fields.Many2one('account.move.line.distribution', string='Reinvoiced move line distribution')
    tag_ids = fields.Many2many('account.analytic.tag','account_analytic_tags_ids', string=' Axis tags4', help='This contains the axis tags for this invoice line.')
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags5', help='This contains the axis tags for this purchase line.')
    
    name = fields.Char(string='Description',
                               related='move_id.sage_name', store= True ,readonly=False,)
    
    
    
    state = fields.Selection(string='State',  related='move_id.state', readonly=True, )
    
    _sql_constraints = [
        (
            'check_credit_debit',
            'CHECK(credit + debit>=0 AND credit * debit=0)',
            'Wrong credit or debit value in accounting entry !'
        ),
        (
            'check_accountable_required_fields',
             "CHECK(COALESCE(display_type IN ('line_section', 'line_note'), 'f') OR account_id IS NOT NULL)",
             "Missing required account on accountable invoice line."
        ),
        (
            'check_non_accountable_fields_null',
             "CHECK(display_type NOT IN ('line_section', 'line_note') OR (amount_currency = 0 AND debit = 0 AND credit = 0 AND account_id IS NULL))",
             "Forbidden unit price, account and quantity on non-accountable invoice line"
        ),
        
        (
            'check_amount_currency_balance_sign',
            'CHECK(credit + debit>=0 AND credit * debit=0)',
            'Wrong credit or debit value in accounting entry !'
        ),
        
        
        
    ]

    
     



    
    def unlink(self):
        """
        Remove any links to batches for the linked reinvoice_move_line_id
        """
        move_ids = self.env['account.move']
        distributions = self.mapped('reinvoice_distribution_id')
        if distributions:
            for distribution in distributions:
                if distribution.move_line_id.move_id:
                    move_ids |= distribution.move_line_id.move_id

            distributions.write({
                'reinvoice_batch_id': False,
                'reinvoice_invoice_line_id': False
            })

        super(AccountInvoiceLine, self).unlink()

        if move_ids:
            move_ids.calculate_reinvoiced_amount()

    
    def _set_additional_fields(self, invoice):

        ret = super(AccountInvoiceLine, self)._set_additional_fields(invoice)

        for line in self:
            if line.purchase_line_id:
                
                if line.purchase_line_id.distribution_cost_ids:
                    # Copy distributions
                    distributions = [(5, 0, 0)]
                    for distribution in line.purchase_line_id.distribution_cost_ids:
                        distributions.append((0, 0, {
                            'child_id': distribution.child_id.id,
                            'percentage': distribution.percentage,
                            'amount_fixed': distribution.amount_fixed,
                        }))

                    line.distribution_cost_ids = distributions
                elif line.purchase_order_id.distribution_cost_ids:
                    # Copy distributions
                    distributions = [(5, 0, 0)]
                    for distribution in line.purchase_order_id.distribution_cost_ids:
                        distributions.append((0, 0, {
                            'child_id': distribution.child_id.id,
                            'percentage': distribution.percentage,
                            'amount_fixed': distribution.amount_fixed,
                        }))

                    line.distribution_cost_ids = distributions

                axes = self.env['account.axis'].search([('company_id', '=', line.purchase_order_id.company_id.id)])
                axis_tags = self.env['account.axis.tag']
                for axis in axes:
                    tags = line.purchase_line_id.all_tag_ids.filtered(lambda r: r.axis_id == axis)
                    if tags:
                        axis_tags |= tags
                    else:
                        tags = line.purchase_order_id.all_tag_ids.filtered(lambda r: r.axis_id == axis)
                        if tags:
                            axis_tags |= tags
                        else:
                            tags = line.purchase_line_id.budget_element_id.all_tag_ids.filtered(lambda r: r.axis_id == axis)
                            if tags:
                                axis_tags |= tags

                if axis_tags:
                    # Copy axis
                    line.all_tag_ids = [(6, 0, [x.id for x in axis_tags])]

                if line.purchase_line_id.budget_element_id.asset_category_id and not line.product_id.asset_category_id:
                    line.asset_category_id = line.purchase_line_id.budget_element_id.asset_category_id.id

        return ret

    
    def add_follower_to_invoice(self):
        for line in self:
            if line.budget_element_id:
                main_budget = False
                if line.budget_element_id.type == 'budget_line':
                    main_budget = line.budget_element_id.budget_id
                elif line.budget_element_id.type == 'budget_detail':
                    main_budget = line.budget_element_id.budget_id.budget_id
                if main_budget:
                    if main_budget.budget_department_id:
                        line.move_id.message_subscribe(partner_ids=[main_budget.budget_department_id.user_id.partner_id.id])
                    line.move_id.message_subscribe(partner_ids=[main_budget.user_id.partner_id.id])

    
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
                        'invoice_line_id': line.id,
                        'parent_id': False,
                    })

    
    def copy_budget_tags(self):
        for line in self:
            # Get best tags
            element = line.budget_element_id
            self.invalidate_cache()  # Wierd things happen if the cache isn't invalidated (element.all_tag_ids return a recordset of budget.element and not account.axis.tag...) - this was found in purchase order line
            while not element.all_tag_ids and element:
                element = element.budget_id

            if element:
                line.all_tag_ids = [(6, 0, [x.id for x in element.all_tag_ids])]

    @api.model
    def create(self, vals):
        """
        Add budget distribution costs (if linked to a purchase order line or a budget element)
        """
        old_orders = self.env['account.move'].browse(vals['move_id']).mapped('invoice_line_ids.purchase_order_id')

        line = super(AccountInvoiceLine, self).create(vals)
        if vals.get('budget_element_id'):
            #line.check_asset_type()
            if line.budget_element_id.company_id != line.move_id.company_id:
                raise UserError(_('Invoices and budget elements must belong to the same company.'))
        if not line.distribution_cost_ids:
            if line.purchase_line_id:
                if line.purchase_line_id.distribution_cost_ids:
                    # Copy distributions
                    distributions = [(5, 0, 0)]
                    for distribution in line.purchase_line_id.distribution_cost_ids:
                        distributions.append((0, 0, {
                            'child_id': distribution.child_id.id,
                            'percentage': distribution.percentage,
                            'amount_fixed': distribution.amount_fixed,
                        }))

                    line.distribution_cost_ids = distributions
                elif line.purchase_order_id.distribution_cost_ids:
                    # Copy distributions
                    distributions = [(5, 0, 0)]
                    for distribution in line.purchase_order_id.distribution_cost_ids:
                        distributions.append((0, 0, {
                            'child_id': distribution.child_id.id,
                            'percentage': distribution.percentage,
                            'amount_fixed': distribution.amount_fixed,
                        }))

                    line.distribution_cost_ids = distributions

            elif line.budget_element_id:
                line.copy_budget_distribution()

        if not line.all_tag_ids and line.budget_element_id:
            line.copy_budget_tags()

        line.sudo().add_follower_to_invoice()  # Sudo required for subscribing users for budgets for which we don't necessarily have access

        if 'all_tag_ids' in vals:
            line.move_id.set_axis_fields()

        # Copy the attachments of the purchase order to the invoice
#         if line.purchase_order_id and line.purchase_order_id not in old_orders:
#             # This is the first time we've added this order - copy the attachment
           
#             self.env['ir.attachment'].search([
#                 ('res_model', '=', 'purchase.order'),
#                 ('res_id', '=', line.purchase_order_id.id),
#             ]).copy(default={
#                 'res_model': 'account.move',
#                 'res_id': line.move_id.id,
#             })

        return line



    @api.model
    def updatetags(self, vals):
        """
        Add budget distribution costs (if linked to a purchase order line or a budget element)
        """
        old_orders = self.env['account.move'].browse(vals['move_id']).mapped('invoice_line_ids.purchase_order_id')

        line = super(AccountInvoiceLine, self).create(vals)
        if vals.get('budget_element_id'):
            #line.check_asset_type()
            if line.budget_element_id.company_id != line.move_id.company_id:
                raise UserError(_('Invoices and budget elements must belong to the same company.'))
        if not line.distribution_cost_ids:
            if line.purchase_line_id:
                if line.purchase_line_id.distribution_cost_ids:
                    # Copy distributions
                    distributions = [(5, 0, 0)]
                    for distribution in line.purchase_line_id.distribution_cost_ids:
                        distributions.append((0, 0, {
                            'child_id': distribution.child_id.id,
                            'percentage': distribution.percentage,
                            'amount_fixed': distribution.amount_fixed,
                        }))

                    line.distribution_cost_ids = distributions
                elif line.purchase_order_id.distribution_cost_ids:
                    # Copy distributions
                    distributions = [(5, 0, 0)]
                    for distribution in line.purchase_order_id.distribution_cost_ids:
                        distributions.append((0, 0, {
                            'child_id': distribution.child_id.id,
                            'percentage': distribution.percentage,
                            'amount_fixed': distribution.amount_fixed,
                        }))

                    line.distribution_cost_ids = distributions

            elif line.budget_element_id:
                line.copy_budget_distribution()

        if not line.all_tag_ids and line.budget_element_id:
            line.copy_budget_tags()

        line.sudo().add_follower_to_invoice()  # Sudo required for subscribing users for budgets for which we don't necessarily have access

        if 'all_tag_ids' in vals:
            line.move_id.set_axis_fields()

        # Copy the attachments of the purchase order to the invoice
#         if line.purchase_order_id and line.purchase_order_id not in old_orders:
#             # This is the first time we've added this order - copy the attachment
           
#             self.env['ir.attachment'].search([
#                 ('res_model', '=', 'purchase.order'),
#                 ('res_id', '=', line.purchase_order_id.id),
#             ]).copy(default={
#                 'res_model': 'account.move',
#                 'res_id': line.move_id.id,
#             })

        return line

    
    def write(self, vals):
        def get_full_name(element):
            if not element:
                return _('None')
            if element.type == 'budget_line':
                return (element.budget_id.name or _('Unknown')) + '/' + element.name
            if element.type == 'budget_detail':
                return (element.budget_id.budget_id.name or _('Unknown')) + '/' + (element.budget_id.name or _('Unknown')) + '/' + element.name
            return element.name

        old_elements = {}
        if 'budget_element_id' in vals:
            for line in self:
                old_elements[line] = line.budget_element_id

        ret = super(AccountInvoiceLine, self).write(vals)

#         self.check_asset_type()
        if vals.get('budget_element_id'):
            for line in self:
                if line.budget_element_id.company_id != line.move_id.company_id:
                    raise UserError(_('Invoices and budget elements must belong to the same company.'))
            self.copy_budget_distribution()
            self.copy_budget_tags()
            self.sudo().add_follower_to_invoice()  # Sudo required for subscribing users for budgets for which we don't necessarily have access

        if 'budget_element_id' in vals:
            for line in self:
                line.move_id.message_post(body=_('Invoice line %s: budget element changed from \'%s\' to \'%s\'.') % (line.name, get_full_name(old_elements[line]), get_full_name(line.budget_element_id)))

        if 'all_tag_ids' in vals:
            self.mapped('move_id').set_axis_fields()

        return ret

    


    @api.onchange('budget_element_id')
    def onchange_budget_element(self):
        self.ensure_one()
        if self.budget_element_id.all_tag_ids:
            # Copy axiss
            self.update({
                'all_tag_ids': [(6, 0, [x.id for x in self.budget_element_id.all_tag_ids])]
            })
        if self.budget_element_id.asset_category_id and not self.asset_category_id and not self.product_id.asset_category_id:
            self.update({
                'asset_category_id': self.budget_element_id.asset_category_id.id
            })

    
    def _asset_create_vals(self):
        """
        Hookable method for filling in assert creation dictionary
        """
        self.ensure_one()
        return {
            'name': self.name,
            'code': self.move_id.number or False,
            'category_id': self.asset_category_id.id,
            'value': self.price_subtotal,
            'partner_id': self.move_id.partner_id.id,
            'company_id': self.move_id.company_id.id,
            'currency_id': self.move_id.currency_id.id,
            'date': self.move_id.date_invoice,
            'move_id': self.move_id.id,
            'invoice_line_id': self.id,
        }



    
    def get_distribution_cost_ids(self):
        self.ensure_one()
        distribution_cost_ids = self.distribution_cost_ids
        if self.distribution_cost_ids:
            distribution_cost_ids = self.distribution_cost_ids
        elif self.move_id.distribution_cost_ids:
            distribution_cost_ids = self.move_id.distribution_cost_ids
        elif self.move_id.distribution_cost_ids:
            distribution_cost_ids = self.move_id.distribution_cost_ids
        elif self.budget_element_id.distribution_cost_ids:
            distribution_cost_ids = self.budget_element_id.distribution_cost_ids
        elif self.budget_element_id.budget_id.distribution_cost_ids:
            distribution_cost_ids = self.budget_element_id.budget_id.distribution_cost_ids
        elif self.budget_element_id.budget_id.budget_id.distribution_cost_ids:
            distribution_cost_ids = self.budget_element_id.budget_id.budget_id.distribution_cost_ids
        elif self.budget_element_id.budget_id.budget_id.budget_id.distribution_cost_ids:
            distribution_cost_ids = self.budget_element_id.budget_id.budget_id.budget_id.distribution_cost_ids
        return distribution_cost_ids



    @api.onchange('product_id')
    def _onchange_product_id(self):
        ret = super(AccountInvoiceLine, self)._onchange_product_id()
        if not self._context.get("use_standard_product_id_change"):
            self.update({
                'name': self.move_id.sage_name
            })

        return ret

    


    @api.model
    def default_get(self, fields_list):
        """
        Get default product
        """
        values = super(AccountInvoiceLine, self).default_get(fields_list)

        if 'product_id' in fields_list and 'product_id' not in values:
            values['product_id'] = self.env.user.company_id.default_expensify_product_id.id

        return values

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
