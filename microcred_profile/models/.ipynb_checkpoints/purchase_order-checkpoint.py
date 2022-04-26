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

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import formatLang, DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime
import logging
_logger = logging.getLogger('microcred_profile')


class PurchaseOrder(models.Model):
    _inherit = ['purchase.order', 'account.axis.tag.wrapper','mail.thread','portal.mixin']
    _name = 'purchase.order'

    microcred_state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('to approve', 'Budgetary validation'),
        ('to approve twice', 'Head validation'),
        ('purchase', 'Ongoing'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string=' microcred State', readonly=True, copy=False, default='draft', tracking=True, compute='_get_microcred_state', store=True)
    state = fields.Selection(selection=[
        # TODO : Put these into English once the translations work...
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('to approve', 'Budgetary validation'),
        ('to approve twice', 'Head validation'),
        ('purchase', 'Ongoing'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string=' State', readonly=True, copy=False, default='draft', tracking=False)
    state_emails = fields.Char(string='Emails', compute='_get_emails')
    currency_amount = fields.Char(string='Currency amount',  compute='_generate_currency_amount')
    child_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags16', store=True, compute='_compute_child_tag_ids',
                                     relation='purchase_order_child_tag_rel', help='This contains the axis tags for this purchase order and its lines.')

    company_currency_id = fields.Many2one(comodel_name='res.currency', string='Company\'s currency', help='The company\'s currency.', related='company_id.currency_id', readonly=True)
    company_amount_untaxed = fields.Monetary(string='Untaxed Amount Company Currency', store=True, readonly=True, compute='_amount_company_all', tracking=True, currency_field='company_currency_id')
    company_amount_tax = fields.Monetary(string='Taxes Company Currency', store=True, readonly=True, compute='_amount_company_all', currency_field='company_currency_id')
    company_amount_total = fields.Monetary(string='Total Company Currency', store=True, readonly=True, compute='_amount_company_all', currency_field='company_currency_id')
    has_different_currency = fields.Boolean(string='Has different currency', compute='_get_different_currency')

    company_amount_invoiced = fields.Monetary(string='Amount Invoiced Company Currency', store=True, readonly=True, compute='_get_invoice_difference', currency_field='company_currency_id')
    company_amount_remaining = fields.Monetary(string='Amount Remaining Company Currency', store=True, readonly=True, compute='_get_invoice_difference', currency_field='company_currency_id')

    referenced_budget_ids = fields.Many2many(comodel_name='budget.element', relation='purchase_order_budget_rel',
                                             string='Referenced budgets', readonly=True, store=True,
                                             compute='_compute_referenced_budgets', help='Budgets referenced by this purchase order.')
    referenced_budget_line_ids = fields.Many2many(comodel_name='budget.element', relation='purchase_order_budget_line_rel',
                                                  string='Referenced budget lines', readonly=True, store=True,
                                                  compute='_compute_referenced_budgets', help='Budget lines referenced by this purchase order.')
    referenced_budget_detail_ids = fields.Many2many(comodel_name='budget.element', relation='purchase_order_budget_detail_rel',
                                                    string='Referenced budget details', readonly=True, store=True,
                                                    compute='_compute_referenced_budgets', help='Budget details referenced by this purchase order.')
    referenced_budget_department_ids = fields.Many2many(comodel_name='budget.element', relation='purchase_order_budget_separtment_rel',
                                                        string='Referenced budget departments', readonly=True, store=True,
                                                        compute='_compute_referenced_budgets', help='Budget departments referenced by this purchase order.')
    order_validator_id = fields.Many2one(comodel_name='res.users', string='Validation user', help='The user validating the order.')
    budget_validator_id = fields.Many2one(comodel_name='res.users', string='Budgetary validation user', help='The user validating the budget of the order.')
    director_validator_id = fields.Many2one(comodel_name='res.users',string='Directorate validation user', help='The director validating the order.')
    order_validate_date = fields.Date(string='Order validation date', help='The validation date.')
    budget_validate_date = fields.Date(string='Budget validation date', help='The validation date.')
    director_validate_date = fields.Date(string='Director validation date', help='The validation date.')

    @api.depends(
        'all_tag_ids',
        'order_line.all_tag_ids'
    )
    def _compute_child_tag_ids(self):
        for order in self:
            order.child_tag_ids = [(6, 0, (order.all_tag_ids | order.mapped('order_line.all_tag_ids')).ids)]

    @api.depends(
        'order_line.price_total',
        'order_line.price_unit',
        'order_line.product_qty',
        'currency_id',
        'currency_id.rate',
        'currency_id.rate_ids',
        'company_id',
        'company_id.currency_id',
    )
    def _amount_company_all(self):
        for order in self:
            current_rate = order.currency_id.with_context({'company_id': order.company_id.id, 'date': order.date_order}).rate or 1.0
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'company_amount_untaxed': order.company_id.currency_id.round(amount_untaxed / current_rate),
                'company_amount_tax': order.company_id.currency_id.round(amount_tax / current_rate),
                'company_amount_total': order.company_id.currency_id.round((amount_tax + amount_untaxed) / current_rate),
            })
    
    
    

        
     
    
    
    def _get_different_currency(self):
        for purchase in self:
            purchase.has_different_currency = (purchase.currency_id != purchase.company_currency_id)

    @api.depends(
        'order_line.budget_element_id'
    )
    def _compute_referenced_budgets(self):
        for order in self:
            budget_details = order.mapped('order_line.budget_element_id').filtered(lambda r: r.type == 'budget_detail')
            budget_lines = order.mapped('order_line.budget_element_id').filtered(lambda r: r.type == 'budget_line') | budget_details.mapped('budget_id')
            budgets = budget_lines.mapped('budget_id')
            budget_departments = budgets.filtered(lambda r: r.budget_department_id is not False).mapped('budget_department_id')
            order.update({
                'referenced_budget_ids': [(6, 0, budgets.ids)],
                'referenced_budget_line_ids': [(6, 0, budget_lines.ids)],
                'referenced_budget_detail_ids': [(6, 0, budget_details.ids)],
                'referenced_budget_department_ids': [(6, 0, budget_departments.ids)],
            })

    @api.depends('state')
    
    def _get_microcred_state(self):
        for purchase in self:
            purchase.microcred_state = purchase.state

    
    def _generate_currency_amount(self):
        for purchase in self:
            purchase.currency_amount = formatLang(self.env, purchase.amount_untaxed, digits=purchase.currency_id.decimal_places or 0, currency_obj=purchase.currency_id, grouping=True, monetary=True)

    
    def _get_emails(self):
        """
        According to state, work out who needs to receive the mails
        """
        for purchase in self:
            groups = self.env['res.groups']
            if purchase.state == 'to approve':
                groups = self.env.ref('microcred_profile.group_microcred_cost_control'),
            elif purchase.state == 'to approve twice':
                groups = self.env.ref('microcred_profile.group_microcred_head_finance'),
            elif purchase.state == 'purchase':
                groups = self.env.ref('microcred_profile.group_microcred_accountant'),

            all_users = self.env['res.users']
            emails = []
            if groups:
                if isinstance(groups, tuple):
                    groups = groups[0]

                users = groups.mapped('users')
                for user in users:
                    if purchase.company_id in user.company_ids and user.email:
                        all_users += user
            if purchase.state == 'purchase':
                # Add creator and any budget element department managers
                if purchase.create_uid not in all_users:
                    all_users += purchase.create_uid
                for line in purchase.order_line:
                    if line.budget_element_id:
                        main_budget = line.budget_element_id.budget_id
                        if main_budget.type == 'budget_line':
                            main_budget = main_budget.budget_id
                        if main_budget.budget_department_id.user_id and main_budget.budget_department_id.user_id not in all_users:
                            all_users += main_budget.budget_department_id.user_id

            if all_users:
                emails = all_users.mapped('email')

            # print(emails)
            purchase.state_emails = emails and ",".join(emails) or ""






    def check_budget_elements(self):
        purchase_order_currencies = {}
        for order in self:
            purchase_order_currencies[order] = order.currency_id.with_context({'company_id': order.company_id.id, 'date': order.date_order}).rate or 1.0

        for purchase_line in self.mapped("order_line"):
            amounts = defaultdict(float)
            if not purchase_line.budget_element_id:
                raise UserError(_('You must include budget elements to all purchase order lines.'))
            amounts[purchase_line.budget_element_id] += purchase_line.order_id.company_id.currency_id.round(purchase_line.price_subtotal / purchase_order_currencies[purchase_line.order_id])

        for budget_element in self.mapped("order_line.budget_element_id"):
            if budget_element.amount_remaining < amounts[budget_element]:
                raise UserError(_('By validating this purchase order, you will go over-budget (budget line: %s, amount remaining: %.2f, over-budget by %.2f).') % (budget_element.name, budget_element.amount_remaining, amounts[budget_element] - budget_element.amount_remaining))

        return True

    
    def button_approve(self):
        """
        Check that (a) that the purchase order is linked to a budget and (b) you won't go over budget
        """
        new_context = self.env.context.copy()
        new_context.pop('search_disable_custom_filters', False)
        new_context.pop('active_domain', False)
        new_context['mail_post_autofollow_really'] = False
        new_context['exclusive_send'] = False
        new_context['lang'] = 'en_EN'

        self.check_budget_elements()

        approved = self.env[self._name]
        for order in self:
            # Deal with triple validation process
            if order.company_id.po_double_validation in ('one_step', 'two_step') \
               or (order.company_id.po_double_validation == 'three_step' and order.amount_total < self.env.user.company_id.currency_id.compute(order.company_id.po_triple_validation_amount, order.currency_id)): 
            #\
               #or order.has_group('purchase.group_purchase_manager'):
                approved += order
                order.write({
                    'budget_validator_id': self.env.user.id,
                    'budget_validate_date': fields.Date.context_today(self),
                })
            else:
                order.write({
                    'state': 'to approve twice',
                    'budget_validator_id': self.env.user.id,
                    'budget_validate_date': fields.Date.context_today(self),
                })
                # print("Send message 2")
                
   
                
                order.with_context(new_context).send_to_next_validators('microcred_profile.email_template_approve_2')
        

        if approved:
            return approved.with_context({'auto_validate': True}).button_second_approve()
        return {}

    
    def send_to_next_validators(self, template_name):
        if not self:
            return
        self.ensure_one()
        template = self.env.ref(template_name, False)
        #template.send_mail(self.ids[0], force_send=True)
        self.message_post_with_template(template.id)

    
    def button_confirm(self):
        self.check_budget_elements()
        new_context = self.env.context.copy()
        new_context.pop('search_disable_custom_filters', False)
        new_context.pop('active_domain', False)
        new_context['mail_post_autofollow_really'] = False
        new_context['exclusive_send'] = False
        new_context['lang'] = 'en_EN'
        for order in self:
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation in ('two_step', 'three_step') and
                        order.amount_total < self.env.user.company_id.currency_id.compute(order.company_id.po_double_validation_amount, order.currency_id)):
            #\
                    #or order.user_has_groups('purchase.group_purchase_manager'):
                order.write({
                    'order_validator_id': self.env.user.id,
                    'order_validate_date':fields.Date.context_today(self),
                })
                order.with_context({'auto_validate': True}).button_second_approve()
            else:
                order.write({
                    'state': 'to approve',
                    'order_validator_id': self.env.user.id,
                    'order_validate_date': fields.Date.context_today(self),
                })
                #print("Send message 1")
                order.with_context(new_context).send_to_next_validators('microcred_profile.email_template_approve_1')
        
                
        return {}

    
    def button_second_approve(self):
        """
        Apply the second approval
        """
        _logger.info('>>>>>>>>>>>>>>> Started approval')
        self.check_budget_elements()
        _logger.info('>>>>>>>>>>>>>>> Checked')
        new_context = self.env.context.copy()
        new_context.pop('search_disable_custom_filters', False)
        new_context.pop('active_domain', False)
        new_context['exclusive_send'] = False
        new_context['mail_post_autofollow_really'] = False
        new_context['lang'] = 'en_EN'
        self.with_context({'do_not_calculate_budgets': True}).write({'state': 'purchase'})
        # print("Send message 3")
        _logger.info('>>>>>>>>>>>>>>> Sending mail')
        self.with_context(new_context).send_to_next_validators('microcred_profile.email_template_approve_3')
        _logger.info('>>>>>>>>>>>>>>> Creating picking')
        #self._create_picking()
        _logger.info('>>>>>>>>>>>>>>> Started ended')
        for order in self:
            period = self.env['account.period'].search([('company_id', '=', order.company_id.id), ('date_start', '<=', order.date_order), ('date_end', '>=', order.date_order)])
            order.mapped('order_line.budget_element_id').with_context({'one_period': period}).calculate_amounts()
        if not self.env.context.get('auto_validate'):
            order.write({
                'director_validator_id': self.env.user.id,
                'director_validate_date': fields.Date.context_today(self),
               
            })
            
        return {}



    
    def write(self, vals):
        ret = super(PurchaseOrder, self).write(vals)
        if 'company_id' in vals:
            for line in self.mapped('order_line'):
                if line.budget_element_id.company_id != line.order_id.company_id:
                    raise UserError(_('Purchase orders and budget elements must belong to the same company.'))

        if 'state' in vals:
            self.mapped('order_line.budget_element_id').calculate_amounts()

        if 'all_tag_ids' in vals or 'child_ids' in vals or 'order_line' in vals:
            self.set_axis_fields()

        return ret

   # @api.model
  #  def _get_tracked_fields(self, updated_fields):
  #      return super(PurchaseOrder, self.with_context(lang='en_EN'))._get_tracked_fields(updated_fields)

    
    def button_done(self):
        """
        Check that all purchase lines have invoices and that these invoices have been paid
        """
        self.write({'state': 'done'})

    @api.depends(
        'order_line',
        'order_line.invoice_lines',
        'order_line.invoice_lines.price_subtotal',
        'order_line.invoice_lines.move_id',
        'order_line.invoice_lines.move_id.state',
        #'move_ids',
        'state',
        'order_line.price_total',
        'order_line.price_unit',
        'order_line.product_qty',
        'currency_id',
        'currency_id.rate',
        'currency_id.rate_ids',
        'company_id',
        'company_id.currency_id',
    )
    def _get_invoice_difference(self):
        """
        Test if the user can view the budget data
        """
        for purchase in self:
            current_rate = purchase.currency_id.with_context({'company_id': purchase.company_id.id, 'date': purchase.date_order}).rate or 1.0
            total_invoiced = 0.0
            for line in purchase.order_line:
                amount_invoiced = 0.0
                for invoice_line in line.invoice_lines.filtered(lambda r: r.move_id.state not in ('draft', 'cancel')):
                    amount = invoice_line.price_subtotal
                    if invoice_line.move_id.move_type in ('in_refund', 'out_refund'):
                        amount = -amount
                    amount_invoiced += amount

                total_invoiced += amount_invoiced

            amount_invoiced = purchase.company_id.currency_id.round(total_invoiced / current_rate)

            if purchase.state not in ('done', 'cancel'):
                purchase.update({
                    'company_amount_invoiced': amount_invoiced,
                    'company_amount_remaining': purchase.company_amount_untaxed - amount_invoiced,
                })
            else:
                purchase.update({
                    'company_amount_invoiced': amount_invoiced,
                    'company_amount_remaining': 0,
                })

    
    ('self', lambda value: value.id)
   

 


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
