# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#              Chris TRIBBECK <chris.tribbeck@syleam.fr>
#
#    This file is a part of microcred_profile
#
#    microcred_profile is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
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

from odoo import models, api, fields, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import float_round, float_compare, float_is_zero
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, formatLang
import odoo.addons.decimal_precision as dp
from collections import defaultdict
from datetime import datetime
import json
import logging
_logger = logging.getLogger('microcred_profile')


#correction ereeur un patenaire ne peux pas suivre le meme object deux fois
class Followers(models.Model):
   _inherit = 'mail.followers'
   @api.model
   def create(self, vals):
        if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
            dups = self.env['mail.followers'].search([('res_model', '=',vals.get('res_model')),
                                           ('res_id', '=', vals.get('res_id')),
                                           ('partner_id', '=', vals.get('partner_id'))])
            if len(dups):
                for p in dups:
                    p.unlink()
        return super(Followers, self).create(vals)


class AccountInvoice(models.Model):
    _inherit = ['account.move', 'account.axis.tag.wrapper','mail.thread']
    _name = "account.move"

    reinvoice_batch_id = fields.Many2one(
        'budget.reinvoice.batch',
        string='Renvoiced batch',
        help='The batch executed using this move line.'
    )
    tag_ids = fields.Many2many(
        comodel_name='account.analytic.tag',
        deprecated=True, string=' Axis tags6',
        help='This contains the axis tags for this invoice line.'
    )
    child_tag_ids = fields.Many2many(
        comodel_name='account.axis.tag',
        string=' Axis tags7',
        store=True,
        compute='_compute_child_tag_ids',
        relation='account_invoice_child_tag_rel',
        help='This contains the axis tags for this invoice and its lines.'
    )
    element_tag_ids = fields.Many2many(
        comodel_name='budget.element.tag',
        deprecated=True,
        domain=[('type', '=', 'other')],
        string='Other tag',
        help=''
    )
    sage_name = fields.Char(
        string='SAGE Name',
        
        help='Enter the name for the export to SAGE',
        
        
    )
    attachment_required = fields.Boolean(
        string='Attachment required',
        help='If checked, an attachment is required.',
        default=True,
    )
    reinvoiced_amount = fields.Float(
        string='Reinvoiced amount',
        digits=("Account"),
        help='The amount this invoice has been reinvoiced.',
        default=0.0
    )
    budget_department_id = fields.Many2one(
        comodel_name='budget.element',
        string='Budget department',
        help='The invoice\'s budget department (if all the same).',
        compute='_get_budget_department_id',
    )
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('posted', 'Accounted'),
        ('validated', 'Validated'),
        ('to pay', 'Payment validated'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string=' Statut', index=True, readonly=True, default='draft',
        tracking=False, copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new"
             " and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used the invoice does not"
             " have an invoice number.\n"
             " * The 'Open' status is used when user create invoice,"
             " an invoice number is generated. Its in open status till user"
             " does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice"
             " is paid. Its related journal entries may or"
             " may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    state_emails = fields.Char(string='Emails', compute='_get_emails')
    head_required = fields.Boolean(string='Head required')
    cost_required = fields.Boolean(string='Cost required')
    dept_required = fields.Boolean(string='Department required')
    was_validated = fields.Boolean(string='Was validated')
    microcred_state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('posted', 'Accounted'),
        ('validated', 'Validated'),
        ('to pay', 'Payment validated'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string=' microcred Status', index=True, readonly=True, default='draft',
        tracking=True, copy=False,
        help=" * The 'Draft' status is used when a user is encoding"
             " a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user create invoice,"
             " an invoice number is generated. Its in open status"
             " till user does not pay invoice.\n"
             " * The 'Validated' status is used once the department"
             " manager has validated the invoice.\n"
             " * The 'Payment validated' status is used when the"
             " invoice is ready to be paid.\n"
             " * The 'Paid' status is set automatically when the"
             " invoice is paid. Its related journal entries may or may not be"
             " reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.",
        compute='_get_microcred_state',
        store=True)
    currency_amount = fields.Char(
        string='Currency amount',
        
        compute='_generate_currency_amount')
    company_currency_id = fields.Many2one(
       comodel_name='res.currency', string='Company\'s currency',
       help='The company\'s currency.', related='company_id.currency_id',
       readonly=True)
    #--------
    
    
    company_amount_untaxed = fields.Monetary(
        string='Untaxed Amount Company Currency',
        store=False, readonly=True, compute='_amount_company_all',
        tracking=True, currency_field='company_currency_id')
    company_amount_tax = fields.Monetary(
        string='Taxes Company Currency', store=False, readonly=True,
        compute='_amount_company_all', currency_field='company_currency_id')
    company_amount_total = fields.Monetary(
        string='Total Company Currency', store=False, readonly=True,
        compute='_amount_company_all', currency_field='company_currency_id')
    
    
    #-----------------
   
    company_amount_residual = fields.Monetary(
        string='Residual Company Currency', store=True, readonly=True,
        compute='_amount_company_all', currency_field='company_currency_id')
    company_amount_untaxed_signed = fields.Monetary(
        string='Untaxed Amount Company Currency (Signed)', store=True,
        readonly=True, compute='_amount_company_all',
        tracking=True,
        currency_field='company_currency_id')
    company_amount_total_signed = fields.Monetary(
        string='Total Company Currency (Signed)', store=True,
        readonly=True, compute='_amount_company_all',
        currency_field='company_currency_id')
    company_amount_residual_signed = fields.Monetary(
        string='Residual Company Currency (Signed)', store=True,
        readonly=True, compute='_amount_company_all',
        currency_field='company_currency_id')
    has_different_currency = fields.Boolean(
        string='Has different currency', compute='_get_different_currency')

    outstanding_credits_debits_widget = fields.Text(
        compute='_get_outstanding_info_JSON')
    payments_widget = fields.Text(compute='_get_payment_info_JSON')
    has_outstanding = fields.Boolean(compute='_get_outstanding_info_JSON')

    referenced_budget_ids = fields.Many2many(
        comodel_name='budget.element', relation='invoice_budget_rel',
        string='Referenced budgets', readonly=True, store=True,
        compute='_compute_referenced_budgets',
        help='Budgets referenced by this invoice.')
    referenced_budget_line_ids = fields.Many2many(
        comodel_name='budget.element', relation='invoice_budget_line_rel',
        string='Referenced budget lines', readonly=True, store=True,
        compute='_compute_referenced_budgets',
        help='Budget lines referenced by this invoice.')
    referenced_budget_detail_ids = fields.Many2many(
        comodel_name='budget.element', relation='invoice_budget_detail_rel',
        string='Referenced budget details', readonly=True, store=True,
        compute='_compute_referenced_budgets',
        help='Budget details referenced by this invoice.')
    referenced_budget_department_ids = fields.Many2many(
        comodel_name='budget.element',
        relation='invoice_budget_separtment_rel',
        string='Referenced budget departments', readonly=True, store=True,
        compute='_compute_referenced_budgets',
        help='Budget departments referenced by this invoice.')
    expensify_id = fields.Many2one(
        comodel_name='expensify.import', string='Expensify import',
        help='The expensify imported that created this invoice (if any).')
    invoice_validator_id = fields.Many2one(
        comodel_name='res.users', string='Invoice validation user',
        help='The user validating the invoice.')
    invoice_validate_date = fields.Date(
        string='Invoice validation date',
        help='The invoice validation date.')
    payment_validator_id = fields.Many2one(
        comodel_name='res.users', string='Validation user',
        help='The user validating the payment.')
    payment_validate_date = fields.Date(
        string='Payment validation date',
        help='The payment validation date.')
    text_distribution = fields.Char(
        string='Specific distribution', size=128,
        help='The specific distribution.', store=True)
      #  compute='_get_text_distribution', )
        
    
    	
    
    
    @api.depends(
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.price_unit',
        'invoice_line_ids.quantity',
        #'tax_line_ids',
        'amount_total',
        'amount_untaxed',
        'amount_tax',
        'amount_residual',
        'currency_id',
        'currency_id.rate',
        'currency_id.rate_ids',
        'company_id',
        'company_id.currency_id',
    )
    def _amount_company_all(self):
        for invoice in self:
            direction = 1.0
            if invoice.move_type in ('out_refund', 'in_refund'):
                direction = -1.0

            current_rate = invoice.currency_id.with_context({
                'company_id': invoice.company_id.id,
                'date': invoice.invoice_date,
            }).rate
            
            curid = invoice.company_id.currency_id
            invoice.update({
                'company_amount_untaxed': curid.round(
                    invoice.amount_untaxed / current_rate),
                'company_amount_tax': curid.round(
                    invoice.amount_tax / current_rate),
                
                'company_amount_total': curid.round(
                    invoice.amount_total / current_rate),
                'company_amount_residual': curid.round(
                    invoice.amount_residual / current_rate),
                'company_amount_untaxed_signed': curid.round(
                    (invoice.amount_untaxed * direction) / current_rate),
                'company_amount_total_signed': curid.round(
                    (invoice.amount_total * direction) / current_rate),
                #'company_amount_residual_signed': curid.round(
                #    (invoice.residual * direction) / current_rate),
            })
                 
        
        
    @api.depends(
        'all_tag_ids',
        'invoice_line_ids',
        'invoice_line_ids.all_tag_ids'
    )
    def _compute_child_tag_ids(self):
        for invoice in self:
            invoice.child_tag_ids = [(6, 0, (
                invoice.all_tag_ids | invoice.mapped(
                    'invoice_line_ids.all_tag_ids')
            ).ids)]

    @api.depends(
        'invoice_line_ids.budget_element_id'
    )
    def _compute_referenced_budgets(self):
        for invoice in self:
            budget_details = invoice.mapped(
                'invoice_line_ids.budget_element_id'
            ).filtered(lambda r: r.type == 'budget_detail')
            budget_lines = (invoice.mapped(
                'invoice_line_ids.budget_element_id'
            ).filtered(lambda r: r.type == 'budget_line') | budget_details.
                mapped('budget_id'))
            budgets = budget_lines.mapped('budget_id')
            budget_departments = budgets.filtered(
                lambda r: r.budget_department_id is not False
            ).mapped('budget_department_id')
            invoice.update({
                'referenced_budget_ids': [(
                    6, 0, budgets.ids)],
                'referenced_budget_line_ids': [(
                    6, 0, budget_lines.ids)],
                'referenced_budget_detail_ids': [(
                    6, 0, budget_details.ids)],
                'referenced_budget_department_ids': [(
                    6, 0, budget_departments.ids)],
            })

    
    def _get_different_currency(self):
        for invoice in self:
            invoice.has_different_currency = (
                invoice.currency_id != invoice.company_currency_id)

    @api.depends('state')
    def _get_microcred_state(self):
        if not self.env.context.get('no_microcred_state_change'):
            for invoice in self:
                invoice.microcred_state = invoice.state
        else:
            for invoice in self:
                invoice.microcred_state = self.env.context.get(
                    'no_microcred_state_change')

    
    def _generate_currency_amount(self):
        for invoice in self:
            invoice.currency_amount = formatLang(
                self.env,
                invoice.amount_untaxed,
                digits=invoice.currency_id.decimal_places or 0,
                currency_obj=invoice.currency_id,
                grouping=True, monetary=True)

    
    def set_required_flags(self):
        """
        According to state, work out who needs to receive the mails
        """
        self.ensure_one()
        dept_required = (
            self.amount_total > self.env.user.company_id.currency_id.compute(
                self.company_id.invoice_validation_department_amount,
                self.currency_id))
        head_required = (
            self.amount_total > self.env.user.company_id.currency_id.compute(
                self.company_id.invoice_validation_head_finance_amount,
                self.currency_id))
        cost_required = not head_required and (
            self.amount_total > self.env.user.company_id.currency_id.compute(
                self.company_id.invoice_validation_cost_control_amount,
                self.currency_id))
        invoice_update = {}
        if dept_required != self.dept_required:
            invoice_update['dept_required'] = dept_required
        if head_required != self.head_required:
            invoice_update['head_required'] = head_required
        if cost_required != self.cost_required:
            invoice_update['cost_required'] = cost_required

        return invoice_update

    
    def check_head_required(self):
        self.ensure_one()
        return self.head_required

    
    def check_cost_required(self):
        self.ensure_one()
        return self.cost_required

    
    def check_dept_required(self):
        self.ensure_one()
        return self.dept_required

    
    def _get_emails(self):
        """
        According to state, work out who needs to receive the mails
        """
        for invoice in self:
            groups = self.env['res.groups']

            all_users = self.env['res.users']
            emails = []
            if invoice.state == 'to pay':
                groups = self.env.ref(
                    'microcred_profile.group_microcred_accountant'),
            elif ((invoice.state == 'open' and not invoice.dept_required) or
                  invoice.state == 'validated'):
                if invoice.head_required:
                    groups = self.env.ref(
                        'microcred_profile.group_microcred_head_finance'),
                elif invoice.cost_required:
                    groups = self.env.ref(
                        'microcred_profile.group_microcred_cost_control'),

            if groups:
                if isinstance(groups, tuple):
                    groups = groups[0]

                users = groups.mapped('users').filtered(
                    lambda r: r.email is not False)
                for user in users:
                    if invoice.company_id in user.company_ids:
                        all_users += user

            elif (invoice.state == 'paid' or (
                  invoice.state == 'open' and invoice.dept_required)):
                follower_partner_ids = invoice.message_follower_ids.mapped(
                    'partner_id'
                ).ids
                users = self.env['res.users'].search([
                    ('partner_id', 'in', follower_partner_ids)
                ]).filtered(lambda r: r.email is not False)
                groups = self.env.ref(
                    'microcred_profile.group_microcred_department_manager')
                for user in users:
                    if (groups in user.groups_id and
                       user.company_id in user.company_ids):
                        all_users += user

            if all_users:
                emails = all_users.mapped('email')

            invoice.state_emails = emails and ",".join(emails) or ""

    
    def send_to_next_validators(self, template_name):
        if not self:
            return
        self.ensure_one()
        new_context = self.env.context.copy()
        new_context['mail_post_autofollow_really'] = False
        new_context['exclusive_send'] = False
        new_context['lang'] = 'en_EN'
        template = self.env.ref(template_name, False)
        self.with_context(new_context).message_post_with_template(template.id)

    
    def unlink(self):
        """
        Remove any links to batches for the linked reinvoice_distribution_id
        """
        distribution_lines = self.mapped(
            'invoice_line_ids.reinvoice_distribution_id')
        if distribution_lines:
            move_ids = distribution_lines.mapped('move_line_id.move_id')
            distribution_lines.write({
                'reinvoice_batch_id': False,
                'reinvoice_invoice_line_id': False
            })
            if move_ids:
                move_ids.calculate_reinvoiced_amount()

        super(AccountInvoice, self).unlink()

    
    def _get_budget_department_id(self):
        for invoice in self:
            department_ids = invoice.mapped(
                'invoice_line_ids.budget_element_id.'
                'budget_id.budget_department_id.id'
            ) + invoice.mapped(
                'invoice_line_ids.budget_element_id.'
                'budget_id.budget_id.budget_department_id.id')
            invoice.budget_department_id = (
                len(department_ids) == 1 and department_ids[0] or False)

    @api.model
    def invoice_line_move_line_get(self):
        results = super(AccountInvoice, self).invoice_line_move_line_get()
        allocate_axis_results = []
        digits_rounding_precision = self.currency_id.rounding
        axis_tag = self.env['account.axis.tag']

        def add_tags(tags, data):
            new_tags = defaultdict(list)
            for tag in data.all_tag_ids:
                new_tags[tag.axis_id.number].append(tag.id)
            for number in new_tags.keys():
                if number not in tags:
                    tags[number] = new_tags[number]

        tag_invoice = False
        if self.move_type in ('out_invoice', 'out_refund'):
            tag_invoice = axis_tag.search([
                ('extra_data', '=', 'customer'),
                ('axis_id.company_id', '=', self.company_id.id)],
                limit=1)
            if not tag_invoice:
                raise UserError(_('Please configure Customer Invoice tags'))

        elif self.move_type in ('in_invoice', 'in_refund'):
            tag_invoice = axis_tag.search([
                ('extra_data', '=', 'supplier'),
                ('axis_id.company_id', '=', self.company_id.id)],
                limit=1)
            if not tag_invoice:
                raise UserError(_('Please configure Supplier Invoice tags'))

        for result in results:
            invoice_line = self.env['account.move.line'].browse(
                result['invl_id'])

            tags = {}
            if tag_invoice:
                tags[tag_invoice[0].axis_id.number] = tag_invoice.ids
            add_tags(tags, invoice_line)
            add_tags(tags, invoice_line.move_id)
            add_tags(tags, invoice_line.budget_element_id)
            add_tags(tags, invoice_line.product_id)
            add_tags(tags, invoice_line.product_id.categ_id)

            main_budget_element = False
            if invoice_line.budget_element_id.type == 'budget_line':
                main_budget_element = invoice_line.budget_element_id.budget_id
            elif invoice_line.budget_element_id.type == 'budget_detail':
                main_budget_element = invoice_line.budget_element_id.\
                    budget_id.budget_id

            if main_budget_element:
                budget_department = main_budget_element.budget_department_id
                if budget_department:
                    add_tags(tags, budget_department)

            distribution_costs = []
            if self.move_type in ('in_invoice', 'in_refund'):
                # Distributions only on supplier invoices and refunds...
                # for the time being...
                distribution_cost_ids = invoice_line.\
                    get_distribution_cost_ids()
                if (distribution_cost_ids and
                   not invoice_line.asset_category_id):
                    # Create fixed distribution costs for this move line
                    # and there's no asset depreciation
                    amount_calculated = 0.
                    highest_price_calculated = False
                    price_calculated = 0.
                    costs_dico = {}
                    for distribution_cost in distribution_cost_ids:
                        if distribution_cost.percentage:
                            price_calculated = float_round(
                                result['price'] * distribution_cost.
                                percentage / 100.,
                                precision_rounding=digits_rounding_precision)
                            amount_calculated += price_calculated
                        elif distribution_cost.amount_fixed:
                            if float_compare(
                                distribution_cost.amount_fixed,
                                result['price'],
                                precision_rounding=digits_rounding_precision
                            ) == 1:
                                raise UserError(_
                                                ("It is impossible to allocate"
                                                 " the amount of %f in the"
                                                 " line %s.\n\nPlease make a"
                                                 " allocation manually"
                                                 ) %
                                                (distribution_cost.
                                                    amount_fixed,
                                                    invoice_line.description))

                            price_calculated = float_round(
                                distribution_cost.amount_fixed,
                                precision_rounding=digits_rounding_precision)
                            amount_calculated += price_calculated

                        costs_dico[distribution_cost] = price_calculated
                        if float_compare(
                            price_calculated,
                            highest_price_calculated,
                            precision_rounding=digits_rounding_precision
                        ) == 1:
                            highest_price_calculated = price_calculated

                    if float_compare(
                        result['price'],
                        amount_calculated,
                        precision_rounding=digits_rounding_precision
                    ):
                        # We have a rounding error - apply it to the
                        # highest distribution cost
                        amount_residual = result['price'] - amount_calculated
                        if highest_price_calculated:
                            costs_dico[
                                highest_price_calculated
                            ] += amount_residual

                    invoice = self.env['account.move'].browse(
                        result['move_id'])
                    rate = 1.0
                    if invoice.currency_id != invoice.company_id.currency_id:
                        rate = invoice.currency_id.with_context({
                            'company_id': invoice.company_id.id,
                            'date': invoice.invoice_date}).rate

                    for distribution_cost in distribution_cost_ids:
                        distribution_costs.append((0, 0, {
                            'budget_partner_id': distribution_cost.child_id.id,
                            'amount_fixed':
                                costs_dico[distribution_cost] / rate,
                        }))

            move_line_dict = dict(result)
            all_tags = []
            for number in tags.keys():
                all_tags.extend(tags[number])

            move_line_dict.update({
                'all_tag_ids': [(6, 0, all_tags)],
                'budget_element_id': invoice_line.budget_element_id.id,
                'invoice_line_id': result['invl_id'],
            })
            if distribution_costs:
                move_line_dict['distribution_partner_ids'] = distribution_costs
            allocate_axis_results.append(move_line_dict)

        return allocate_axis_results

    @api.model
    def line_get_convert(self, line, part):
        if line.get('type') in ('dest', 'tax'):
            line['name'] = self.browse(
                line['move_id']).sage_name or line['name']
        result = super(AccountInvoice, self).line_get_convert(
            line=line, part=part)
        result.update({'all_tag_ids': line.get('all_tag_ids', False)})
        result.update({'budget_element_id':
                      line.get('budget_element_id', False)})
        result.update({'distribution_partner_ids':
                      line.get('distribution_partner_ids', False)})
        result.update({'invoice_line_id': line.get('invoice_line_id', False)})
        return result

    
    def update_batch_invoice(self):
        """
        Recreate reinvoicing invoices
        """
        for invoice in self:
            if invoice.reinvoice_batch_id:
                invoice.reinvoice_batch_id.update_batch_invoice(invoice)

   
    
    def check_invoice_information(self, next_step=False):
        """
        Verify certain data on the invoices
        """
        
        # Check that there is an attachment (unless it's a customer invoice
        # or an expensify invoice)
        is_admin = (self.env.user.id == SUPERUSER_ID or
                    self.env.ref(
                        'microcred_profile.'
                        'group_microcred_admin'
                    ) in self.env.user.groups_id or
                    self.env.ref(
                        'microcred_profile.'
                        'group_microcred_accountant'
                    ) in self.env.user.groups_id)
        # id_admin = False
        attachments = self.env['ir.attachment']
        for invoice in self:
            rounding_precision = invoice.company_id.currency_id.rounding
            if invoice.attachment_required:
                attachments = attachments.search([
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', invoice.id),
                ])
                if not attachments:
                    raise UserError(_(
                        'There are no attachments to this invoice.'))
            if invoice.move_type == 'in_invoice':
                invoice_list = self.search([
                    ('state', '!=', 'cancel'),
                    ('move_type', '=', 'in_invoice'),
                    ('reference', '=', invoice.reference)])
                if len(invoice_list) > 1:
                    raise UserError(_(
                        'There is more than one invoice with'
                        ' this reference ({reference}).'
                    ).format(reference=invoice.reference))
                if not invoice.sage_name:
                    raise UserError(_('You must supply a SAGE name.'))
                if not invoice.partner_id.thirdparty_account:
                    raise UserError(_(
                        'The supplier must have a third-party account.'))

                if invoice.state == 'draft':
                    # Only checked on validating the invoice
                    amounts = defaultdict(float)
                    for invoice_line in self.mapped("invoice_line_ids"):
                        if not invoice_line.purchase_line_id:
                            # Doit l'ajouter au montant
                            amounts[invoice_line.budget_element_id] += \
                                invoice_line.price_unit * invoice_line.quantity

                    for budget_element in self.mapped(
                        'invoice_line_ids.budget_element_id'
                    ):
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

            if not is_admin and invoice.state == 'draft':
                # Only on validating the invoice
                bad_invoice_lines = self.mapped(
                    'invoice_line_ids').filtered(
                        lambda r: r.purchase_line_id.id is False)
                if bad_invoice_lines:
                    raise UserError(_(
                        'There are invoice lines which are not'
                        ' linked to purchase orders.'
                        ' Only administrators can validate such invoices.'))
                purchase_line_ids = invoice.invoice_line_ids.mapped(
                    'purchase_line_id')
                error_lines = []
                for purchase_line in purchase_line_ids:
                    amount_invoiced = 0.0
                    invoice_list = []
                    for invoice_line in purchase_line.invoice_lines.filtered(
                        lambda r: (r.move_id.state in (
                            'validated',
                            'open',
                            'paid',
                            'to_pay'
                        ) or
                            r.move_id == invoice) and
                            r.price_subtotal != 0.0):
                        amount = invoice_line.price_subtotal
                        if invoice.move_type in ('in_refund', 'out_refund'):
                            amount = -amount
                        invoice_list.append(_('%s (%.2f)') % (
                            invoice_line.move_id.reference,
                            amount))
                        amount_invoiced += amount

                    if amount_invoiced > purchase_line.price_subtotal:
                        error_lines.append(_(
                            'Purchase order %s, product %s,'
                            ' amount ordered = %.2f : amount invoiced'
                            ' = %.2f on invoice(s):\n --- %s'
                        ) % (
                            purchase_line.order_id.name,
                            purchase_line.product_id.name,
                            purchase_line.price_subtotal,
                            amount_invoiced,
                            ',\n --- '.join(invoice_list)))
                if error_lines:
                    raise UserError(_(
                        'Problems with the amounts ordered'
                        ' and the amounts invoices have been'
                        ' detected in the following purchase'
                        ' order line(s) and invoice(s):\n\n*'
                        ' %s\n\nYou cannot proceed with the validation.'
                    ) % ('\n\n- '.join(error_lines)))

            if next_step == 'open':
                if not invoice.invoice_date:
                    raise UserError(_(
                        'You must set the invoice date before'
                        ' recording the invoice.'))
                if not invoice.invoice_date_due:
                    raise UserError(_(
                        'You must set the due date before'
                        ' recording the invoice.'))
                if invoice.move_type == 'in_invoice':
                    for line in invoice.invoice_line_ids:
                        if (line.asset_category_id and
                            not line.budget_element_id.asset_category_id
                            ) or \
                           (not line.asset_category_id and
                           line.budget_element_id.asset_category_id):
                            raise UserError(_(
                                'Lines and budget elements either'
                                ' must both have assets or neither.'))

        for invoice_line in self.mapped("invoice_line_ids"):
            if invoice_line.move_id.move_type in ('in_invoice', 'in_refund'):
                if not invoice_line.budget_element_id:
                    raise UserError(_(
                        'You must include budget elements to all'
                        ' invoice lines.'))
                if next_step == 'open':
                    if invoice.company_id.distribution_required:
                        distributions = invoice_line.distribution_cost_ids
                        if not distributions:
                            raise UserError(_(
                                'You must set cost distributions'
                                ' to all invoice lines.'))

        return True

    
    def action_move_create(self):
        """ Copy name to reference if empty and customer invoice/refund """

        self.check_invoice_information(next_step='open')
        _logger.info('>>>>>>>>>>>>>>> Started creating')
        for inv in self:
            if inv.move_type in ('out_invoice', 'out_refund') and not inv.reference:
                inv.reference = inv.name
        ret = super(AccountInvoice, self.with_context({
            'do_not_calculate_budgets': True})).action_move_create()
        _logger.info('>>>>>>>>>>>>>>> Ended creating')
        budget_elements = self.mapped(
            'invoice_line_ids.budget_element_id'
        ) + self.env['account.asset'].search([
            ('invoice_line_id', 'in', self.mapped(
                'invoice_line_ids.id'))]).mapped(
                    'depreciation_line_ids.budget_element_id')
        budget_elements.calculate_amounts()
        _logger.info('>>>>>>>>>>>>>>> Ended calculating')
        return ret

    
    def invoice_validate(self):
        """
        Check that the invoice can be validated
        and that there are budget elements
        """

        _logger.info('>>>>>>>>>>>>>>> Started validating')
        mail_list = self.filtered(
            lambda r: r.state == 'draft' and r.dept_required)
        ret = super(AccountInvoice, self).invoice_validate()
        _logger.info('<<<<<<<<<<<<<<< Ended validating')

        """
        Send any mails
        """
        self.invalidate_cache()
        for invoice in mail_list:
            invoice.state_emails
            # Force recalculation of state_emails...
            # Otherwise it's not done in the filling in of the template
            invoice.send_to_next_validators(
                'microcred_profile.'
                'email_template_invoice_request_dept_validation')
        expensify = self.mapped('expensify_id')
        if expensify:
            expensify.write({
                'state': 'done',
            })
        return ret
    
    
    def _check_balanced(self):
        return True

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Set the sage_name
        """
        for invoice in self:
            invoice.sage_name = (invoice.partner_id.name or '').upper()

    @api.model
    def create(self, vals):
        """
        Set the attachments_required field
        """
        new_invoice = super(AccountInvoice, self).create(vals)
    
        if 'attachment_required' not in 'vals' and new_invoice.move_type not in (
                'in_invoice', 'in_refund'):
            new_invoice.attachment_required = False

        """
        Check for auto-subscriptions
        """
        partner_ids = self.env['res.users'].sudo().search([
            ('autosubscribe_invoices', '=', True)]).mapped(
                'user_group_ids.partner_id').ids + \
            new_invoice.mapped(
                'invoice_line_ids.budget_element_id.'
                'message_follower_ids.partner_id').ids
        if partner_ids:
            new_invoice.sudo().message_subscribe(
                partner_ids=partner_ids)

        return new_invoice

    
    def write(self, vals):
        ret = super(AccountInvoice, self).write(vals)
        if 'company_id' in vals:
            for line in self.mapped('invoice_line_ids'):
                if (line.budget_element_id and
                    line.budget_element_id.company_id !=
                        line.move_id.company_id):
                    raise UserError(_(
                        'Invoices and budget elements must'
                        ' belong to the same company.'))

        if ('all_tag_ids' in vals or
            'child_tag_ids' in vals or
                'invoice_line_ids' in vals):
            self.set_axis_fields()

        for invoice in self:
            new_vals = invoice.set_required_flags()
            if new_vals:
                super(AccountInvoice, invoice).write(new_vals)

        return ret
    
    
    
  
    
    def calculate_reinvoiced_amount(self):
        for invoice in self:
            amount = 0.0
            for line in invoice.move_id.line_ids:
                if line.reinvoice_batch_ids:
                    amount += line.debit or line.credit
            invoice.reinvoiced_amount = amount

    
    def action_validate(self):
        """
        This is the passing of the invoice from "open" just to "validated"
        """
        self.check_invoice_information(next_step='validated')
        mail_list = self.filtered(
            lambda r: r.state == 'open' and (
                r.head_required or r.cost_required))
        self.write({
            'state': 'validated',
            'invoice_validator_id': self.env.user.id,
            'invoice_validate_date': datetime.today().strftime(DF),
        })
        for invoice in mail_list:
            invoice.send_to_next_validators(
                'microcred_profile.'
                'email_template_invoice_request_mgt_validation')
        return True

    
    def action_to_pay(self):
        mail_list = self.filtered(
            lambda r: r.state != 'to pay' and (
                r.dept_required or r.head_required or r.cost_required))
        self.write({
            'state': 'to pay',
            'payment_validator_id': self.env.user.id,
            'payment_validate_date': datetime.today().strftime(DF),
        })
        for invoice in mail_list:
            invoice.send_to_next_validators(
                'microcred_profile.email_template_invoice_approved')
        return True

    
    def action_create_payments(self):
#         mail_list = self.filtered(lambda r: r.state != 'paid')
        ret = super(AccountInvoice, self).action_create_payments()
        self.invalidate_cache()
#         for invoice in mail_list:
#             invoice.state_emails
#             # Force recalculation of state_emails...
#             # Otherwise it's not done in the filling in of the template
#             invoice.send_to_next_validators(
#                 'microcred_profile.email_template_invoice_paid')

        purchase_orders = self.mapped('invoice_line_ids.purchase_id')
        for order in purchase_orders:
            if float_is_zero(
                order.company_amount_remaining,
                    precision_digits=2):
                order.button_done()

        return ret

    
    ('self', lambda value: value.id)


   

   # @api.model
   # def _get_tracked_fields(self, updated_fields):
   #     return super(AccountInvoice, self.with_context(
    #        lang='en_EN'))._get_tracked_fields(updated_fields)

    


    #@api.onchange('purchase_id')
    def purchase_order_change(self):


        if self.journal_id:
            (self.currency_id == self.journal_id.currency_id.id or
             self.journal_id.company_id.currency_id.id)

        if self.purchase_id and False:
            if self.invoice_line_ids:
                if self.purchase_id.currency_id != self.currency_id:
                    raise UserError(_(
                        'You can only add purchase orders with'
                        ' the same currency as that of the invoice.'))
            self.update({
                'currency_id': self.purchase_id.currency_id.id,
            })

        ret = super(AccountInvoice, self).purchase_order_change()
        return ret

    @api.onchange('currency_id', 'invoice_date')
    def _onchange_currency_id(self):
        if self.currency_id:
            for line in self.invoice_line_ids.filtered(
                    lambda r: r.purchase_line_id):
                line.price_unit = line.purchase_order_id.currency_id.with_context(
                    date=self.invoice_date).compute(
                        line.purchase_line_id.price_unit,
                        self.currency_id, round=False)


    def _get_outstanding_info_JSON(self):
        # NOTE : This code is copied from the standard account_invoice
        # but can only be displayed in the "to pay" state
        self.outstanding_credits_debits_widget = json.dumps(False)
        if ((self.move_type in ('in_invoice', 'in_refund') and
            self.state == 'to pay') or
            (self.move_type in ('out_invoice', 'out_refund') and
             self.state == 'open')):
            domain = [
                ('account_id', '=', self.account_id.id),
                ('partner_id', '=', self.env[
                    'res.partner']._find_accounting_partner(
                        self.partner_id).id),
                ('reconciled', '=', False),
                ('amount_residual', '!=', 0.0)]
            if self.move_type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [],
                    'move_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if (line.currency_id and
                            line.currency_id == self.currency_id):
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        amount_to_show = line.company_id.currency_id.\
                            with_context(
                                date=line.date).compute(
                                    abs(line.amount_residual),
                                    self.currency_id)
                    if float_is_zero(
                            amount_to_show,
                            precision_rounding=self.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False,
                        submenu=False):
        def get_view_id(xid, name):
            try:
                return self.env.ref('account.' + xid)
            except ValueError:
                view = self.env['ir.ui.view'].search([
                    ('name', '=', name)],
                    limit=1)
                if not view:
                    return False
                return view.id

        if self.env.context.get('use_customer'):
            view_id = get_view_id('invoice_form', 'account.move.form').id

        return super(AccountInvoice, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar, submenu=submenu)

    @api.depends(
        'invoice_line_ids.distribution_cost_ids',
        'invoice_line_ids',
        'move_id',
        'move_id.line_ids',
        'move_id.line_ids.distribution_partner_ids',
    )
    def _get_text_distribution(self):
        """
        Calculate the text containing the distribution (if specific).
        """
        for invoice in self:
            distributions = defaultdict(float)
            text_distributions = []
            total = 0.0
            if not invoice.id:
                for line in invoice.invoice_line_ids:
                    for distribution in line.distribution_cost_ids:
                        distributions[distribution.child_id] += \
                            distribution.amount_calculated
                        total += distribution.amount_calculated
            else:
                for line in invoice.move_id.line_ids:
                    for distribution in line.distribution_partner_ids:
                        distributions[distribution.budget_partner_id] += \
                            distribution.amount_fixed
                        total += distribution.amount_fixed

            for distribution in distributions:
                text_distributions.append(_(
                    '%s: %.2f%% (%.2f)') % (
                        distribution.name,
                        float_round(
                            (distributions[distribution] * 100.0) /
                            (total or 0.1),
                            precision_digits=2),
                    float_round(distributions[distribution],
                                precision_digits=2)))

            if distributions:
                invoice.text_distribution = ', '.join(text_distributions)
            else:
                invoice.text_distribution = _("None")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
