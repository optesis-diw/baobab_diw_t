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

from odoo import models, fields, api, SUPERUSER_ID
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.osv import expression


class BudgetElement(models.Model):
    _name = 'budget.element'
    _description = 'Budget element'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', size=128, help='Enter the budget element\'s name.', required=True, )
    code = fields.Char(string='Code', size=32, help='Enter the budget element\'s code.', )
    type_id = fields.Many2one('budget.element.type', string=' Type de budget ', help='Select the budget element\'s type', required=True, )
    #type = fields.Selection([
    #    ('periodic', 'Periodic'),
    #    ('project', 'Project'),
    #    ('budget_line', 'Budget line'),
    #    ('budget_detail', 'Budget detail'),
    #    ('department', 'Department'),
    #    ('partner', 'Partner'),
    #], string=' Type budget ', help='Select the budget element\'s type.', related='type_id.type')
    type = fields.Selection(string=' Type budget ', help='Select the budget element\'s type.', related='type_id.type')

    user_id = fields.Many2one('res.users', string='Manager', help='Select the manager', required=True, default=lambda self: self.env.user, )
    amount_fixed = fields.Float(string='Fixed amount',  digits=(100,2), help='Enter the fixed amount.')
    amount_initial = fields.Float(string='Initial amount',  digits=(100,2), help='The initial amount.', readonly=True, )
    amount_current = fields.Float(string='Current amount',  digits=(100,2), help='The current amount.')
    amount_engaged = fields.Float(string='Engaged amount',  digits=(100,2), help='The engaged amount.', compute='_get_amounts', )
    amount_invoiced = fields.Float(string='Invoiced amount',  digits=(100,2), help='The invoiced amount.', compute='_get_amounts', )
    amount_calculated = fields.Float(string='Calculated amount',  digits=(100,2), compute='_get_amount_calculated', )
    amount_remaining = fields.Float(string='Remaining amount',  digits=(100,2), compute='_get_amounts', )
    date_start = fields.Date(string='Start date', help='Enter the start date.')
    date_end = fields.Date(string='End date', help='Enter the end date.')
    project_id = fields.Many2one('project.project', string='Project', help='Select the project.')
    department_id = fields.Many2one('hr.department', string='Department', help='Select the department.')
    partner_id = fields.Many2one('res.partner', string='Partner', help='Select the partner.')
    product_id = fields.Many2one('product.product', string='Product', help='Select the product.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('proposition', 'Proposition'),
        ('open', 'Open'),
        ('done', 'Closed'),
        ('cancel', 'Cancelled'),
    ], string='State', help='The budget element\'s state.', default='draft', tracking=True, )
    budget_line_ids = fields.One2many('budget.element', 'budget_id', string='Budget lines', help='Select budget lines.', domain=[('type_id.type', '=', 'budget_line')])
    budget_detail_ids = fields.One2many('budget.element', 'budget_id', string='Budget details', help='Select budget details.', domain=[('type_id.type', '=', 'budget_detail')])
    budget_id = fields.Many2one('budget.element', string='Primary budget', help='Select the primary budget.')
    text_distribution = fields.Char(string='Specific distribution', size=128, help='The specific distribution.', compute='_get_text_distribution', )
    member_ids = fields.One2many('budget.element.member', 'element_id', string='Members', help='Select the members and their access levels.' )
    distribution_cost_ids = fields.One2many('budget.element.distribution', 'parent_id', string='Department/Partner distribution',
                                            help='Enter the department/partner distributions for this budget.',
                                            domain=[('type', '=', 'cost')])
    distribution_budget_ids = fields.One2many('budget.element.distribution', 'parent_id', string='Budget distribution',
                                              help='Enter the budget distributions for this budget.',
                                              domain=[('type', '=', 'budget')])
    affected_budget_ids = fields.One2many('budget.element.distribution', 'child_id', string='Budget affections', help='The budgets affected to this budget.')
    user_can_modify = fields.Boolean(string='User can view', compute='_get_user_can_view', )
    linked_distribution_id = fields.Many2one('budget.element.distribution', string='Linked budget',  )  # Used for creating a budget line per affected budget
    is_readonly = fields.Boolean(string='Readonly')
    was_opened = fields.Boolean(string='Was opened')
    copy_initial = fields.Boolean(string='Copy initial', default=True)
    purchase_line_ids = fields.One2many('purchase.order.line', 'budget_element_id', string='Purchase order lines')
    invoice_line_ids = fields.One2many('account.move.line', 'budget_element_id', string='Invoice lines')
    has_details = fields.Boolean(string='Has details', compute='_get_has_details', )
    purchase_count = fields.Integer(string='Purchases', help='The number of purchase orders.', compute='_get_invoice_purchase_count', )
    invoice_count = fields.Integer(string='Invoices', help='The number of invoices.', compute='_get_invoice_purchase_count', )
    company_id = fields.Many2one('res.company', string='Company', help='The company to whom the budget is associated.',
                                 default=lambda self: self.env.company.id)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('code', '=ilike', name + '%'), ('name', 'ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
            budgets = self.search(domain)
            if budgets:
                budgets += budgets.mapped('budget_line_ids') + budgets.mapped('budget_detail_ids') + budgets.mapped('budget_line_ids.budget_detail_ids')
            if budgets:
                return self.search([('id', 'in', budgets.ids)] + args, limit=limit).name_get()
        budgets = self.search(domain + args, limit=limit)
        return budgets.name_get()

    
    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for element in self:
            full_name = element.name
            if element.code:
                full_name = '[%s] %s' % (element.code, element.name)
            if element.type_id.type == 'budget_line':
                full_name = '%s/%s' % (element.budget_id.name or _('Unknown'), full_name)
            elif element.type_id.type == 'budget_detail':
                full_name = '%s/%s/%s' % (element.budget_id.budget_id.name or _('Unknown'), element.budget_id.name or _('Unknown'), full_name)
            result.append((element.id, full_name))
        return result

    @api.onchange('department_id')
    def onchange_department_id(self):
        """
        Set the manager to that of the department's head
        """
        self.ensure_one()
        if self.department_id:
            if self.department_id.manager_id.user_id:
                self.user_id = self.department_id.manager_id.user_id.id

    @api.onchange('project_id')
    def onchange_project_id(self):
        """
        Set the manager to that of the department's head
        """
        self.ensure_one()
        if self.project_id:
            if self.project_id.user_id:
                self.user_id = self.project_id.user_id.id
                self.name = self.project_id.name

    
    def _get_allowed_states(self):
        """
        Over-rideable function for getting allowed states in purchase orders and invoices
        """
        return(
            ('purchase', 'done'),
            ('open', 'paid'),
        )

    
    @api.depends(
        'purchase_line_ids.order_id.currency_id',
        'purchase_line_ids.order_id.state',
        'purchase_line_ids.budget_element_id',
        'purchase_line_ids.price_subtotal',
        'invoice_line_ids.move_id.currency_id',
        'invoice_line_ids.move_id.state',
        'invoice_line_ids.budget_element_id',
        'invoice_line_ids.price_subtotal',
        'budget_line_ids.amount_engaged',
        'budget_detail_ids.amount_engaged',
        'budget_line_ids.amount_invoiced',
        'budget_detail_ids.amount_invoiced',
        'budget_line_ids.amount_fixed',
        'budget_detail_ids.amount_fixed',
        'budget_line_ids',
        'budget_detail_ids',
        'amount_engaged',
        'amount_invoiced',
        'amount_fixed'
    )
    def _get_amounts(self):
        """
        Calculate the engaged, invoiced and remaining amounts
        """
        (purchase_order_states, invoice_states) = self._get_allowed_states()

        for element in self:
            engaged_amount = 0.0
            invoiced_amount = 0.0
            if element.type in ('budget_line', 'budget_detail'):
                if not element.linked_distribution_id:
                    purchased_amount = 0.0
                    remove_amount = 0.0
                    linked_invoice_line_ids = self.env['account.move.line']
                    # Calculate from purchase order lines
                    all_element_ids = [element.id]
                    all_element_ids.extend(element.mapped('budget_detail_ids.id'))
                    purchase_lines = self.env['purchase.order.line'].sudo().search([
                        ('budget_element_id', 'in', all_element_ids), ('order_id.state', 'in', purchase_order_states)])
                    for line in purchase_lines:
                        current_rate = 1.0
                        if line.order_id.currency_id != element.company_id.currency_id:
                            current_rate = line.order_id.currency_id.with_context({'date': line.order_id.date_order}).rate
                        purchased_amount += element.company_id.currency_id.round(line.price_subtotal / current_rate)
                        linked_invoice_line_ids += line.mapped('invoice_lines')
                    # Remove any linked invoices
                    invoice_lines = self.env['account.move.line'].sudo().search(
                        [('budget_element_id', 'in', all_element_ids), ('move_id.state', 'in', invoice_states)])
                    for line in invoice_lines:
                        current_rate = 1.0
                        if line.move_id.currency_id != element.company_id.currency_id:
                            current_rate = line.move_id.currency_id.with_context({'date': line.move_id.date_invoice}).rate
                        amount = element.company_id.currency_id.round(line.price_subtotal / current_rate)
                        if line.move_id.type in ('in_refund', 'out_refund'):
                            amount = -amount
                        invoiced_amount += amount
                        if line in linked_invoice_line_ids:
                            remove_amount += amount
                    engaged_amount = purchased_amount - remove_amount
                    # print('%d\t%.2f\t%.2f\t%.2f\t%s' % (element.id, engaged_amount, invoiced_amount, remove_amount, element.name))
                else:
                    engaged_amount = element.linked_distribution_id.amount_engaged
                    invoiced_amount = element.linked_distribution_id.amount_invoiced

            else:
                # Calculate from budget lines (sub-budgets are included as budget lines)
                # Budget lines
                for line in element.budget_line_ids:
                    engaged_amount += line.amount_engaged
                    invoiced_amount += line.amount_invoiced
            element.update({
                'amount_engaged': engaged_amount,
                'amount_invoiced': invoiced_amount,
                'amount_remaining': element.amount_fixed - (engaged_amount + invoiced_amount)
            })
            # print('%d\t%.2f\t%.2f\t%.2f\t%s' % (element.id, element.amount_engaged, element.amount_invoiced, element.amount_remaining, element.name))

    
    def _get_has_details(self):
        """
        Define whether the budget line has details or not
        """
        for element in self:
            element.has_details = (len(element.budget_detail_ids) > 0)

    
    def _get_invoice_purchase_count(self):
        """
        Calculate the number of invoices and purchases
        """
        for element in self:
            element_ids = element.mapped('budget_line_ids.budget_detail_ids.id') + element.mapped('budget_line_ids.id') + element.mapped('budget_detail_ids.id') + element.mapped('id')

            move_ids = self.env['account.move.line'].search([('budget_element_id', 'in', element_ids)]).mapped('move_id.id')
            element.invoice_count = len(move_ids)
            purchase_ids = self.env['purchase.order.line'].search([('budget_element_id', 'in', element_ids)]).mapped('order_id.id')
            element.purchase_count = len(purchase_ids)

    
    def _get_user_can_view(self):
        """
        Test if the user can view the budget data
        """
        for element in self:
            can_modify = False
            if self.env.user.id == SUPERUSER_ID:
                can_modify = True
            elif self.env.user in element.member_ids.filtered(lambda record: record.access_level == 'can_modify').mapped('user_id'):
                can_modify = True

            element.user_can_modify = can_modify

    
    def _get_text_distribution(self):
        """
        Calculate the text containing the distribution (if specific).
        """
        for element in self:
            distributions = []
            for distribution in element.distribution_cost_ids:
                if distribution.amount_fixed:
                    distributions.append(_('%s: %.2d') % (distribution.child_id.name, distribution.amount_fixed))
                else:
                    distributions.append(_('%s: %.2d%% (%.2d)') % (distribution.child_id.name, distribution.percentage, distribution.amount_fixed or distribution.amount_calculated))

            if not distributions and element.linked_distribution_id:
                for distribution in element.linked_distribution_id.parent_id.distribution_cost_ids:
                    if distribution.amount_fixed:
                        distributions.append(_('%s: %.2d') % (distribution.child_id.name, distribution.amount_fixed))
                    else:
                        distributions.append(_('%s: %.2d%% (%.2d)') % (distribution.child_id.name, distribution.percentage, distribution.amount_fixed or distribution.amount_calculated))

            if distributions:
                element.text_distribution = ', '.join(distributions)
            else:
                element.text_distribution = _("None")

    
    def _get_amount_calculated(self):
        """
        Calculate the amount (either fixed or calculated)
        """

        for element in self:
            total = 0.0
            if element.type in ('periodic', 'project'):
                for line in element.budget_line_ids:
                    if line.amount_fixed:
                        total += line.amount_fixed
                    else:
                        for detail in element.budget_detail_ids:
                            total += detail.amount_fixed

            elif element.type == 'budget_line':
                if element.amount_fixed:
                    total = element.amount_fixed
                else:
                    for line in element.budget_detail_ids:
                        total += line.amount_fixed

            elif element.type == 'budget_detail':
                total = element.amount_fixed

            element.amount_calculated = total
        return total

    
    def check_manager(self):
        """
        Check that the manager has modify access to the budget element
        """

        for element in self:
            if element.user_id not in element.member_ids.mapped('user_id'):
                # Need to add to it
                self.env['budget.element.member'].create({
                    'user_id': element.user_id.id,
                    'access_level': 'can_modify',
                    'element_id': element.id,
                })
            else:
                # Set it to modify access
                element.member_ids.filtered(lambda user: user.user_id == element.user_id).write({'access_level': 'can_modify'})

    
    def check_coherences(self, vals):
        """
        Check there is not "wierd" data
        """
        if vals.get('type') or 'project_id' in vals or 'department_id' in vals or 'partner_id' in vals:
            for element in self:
                new_vals = {}
                if element.type != 'project':
                    new_vals['project_id'] = False
                if element.type != 'department':
                    new_vals['department_id'] = False
                if element.type != 'partner':
                    new_vals['partner_id'] = False
                return super(BudgetElement, element).write(new_vals)

    @api.model
    def create(self, vals):
        """
        """

        new_element = super(BudgetElement, self).create(vals)
        new_element.check_coherences(vals)

        # Check that the manager can modify the current budget
        if new_element.type in ('periodic', 'project'):
            new_element.check_manager()

        # If budget line or budget details, get certain informations from the parent
        if new_element.type in ('budget_line', 'budget_detail') and new_element.budget_id:
            new_vals = {
                'date_start': new_element.budget_id.date_start,
                'date_end': new_element.budget_id.date_end,
                'project_id': new_element.budget_id.project_id.id,
                'department_id': new_element.budget_id.department_id.id,
                'user_id': new_element.budget_id.user_id.id,
                'partner_id': new_element.budget_id.partner_id.id,
                'company_id': new_element.budget_id.company_id.id,
            }
            new_element.write(new_vals)

        return new_element

    
    def calculate_linked_amounts(self, vals=None):
        """
        Calculate the amount in a linked budget line
        """
        if vals is None:
            vals = {}

        for line in self:
            line_vals = {}
            if 'amount_fixed' in vals or 'amount_calculated' in vals:
                line_vals['amount_fixed'] = line.linked_distribution_id.amount_fixed or line.linked_distribution_id.amount_calculated
            if 'name' in vals:
                line_vals['name'] = vals['name']
            line.sudo().write(line_vals)  # We may not have direct rights to the line...

    
    def write(self, vals):
        """
        """

        ret = super(BudgetElement, self).write(vals)
        self.check_coherences(vals)

        # Check that the manager can modify the current budget
        for element in self:
            if element.type in ('periodic', 'project'):
                element.check_manager()

        # Check if this budget is linked to anything (and we've updated the fixed amount)
        if 'amount_fixed' in vals or 'amount_calculated' in vals or 'name' in vals:
            for element in self:
                if element.state == 'draft':
                    super(BudgetElement, self).write({
                        'amount_initial': element.amount_fixed
                    })
            self.mapped('distribution_budget_ids.linked_budget_line_ids').calculate_linked_amounts(vals=vals)

        # If budget line or budget details, get certain informations from the parent, if the parent has changed
        if 'budget_id' in vals:
            for element in self:
                if element.type in ('budget_line', 'budget_detail'):
                    new_vals = {
                        'date_start': element.budget_id.date_start,
                        'date_end': element.budget_id.date_end,
                        'project_id': element.budget_id.project_id.id,
                        'department_id': element.budget_id.department_id.id,
                        'user_id': element.budget_id.user_id.id,
                        'partner_id': element.budget_id.partner_id.id,
                        'company_id': element.budget_id.company_id.id,
                    }
                    super(BudgetElement, element).write(new_vals)

        # If cascadeable elements have been modified, cascade the changes
        cascadeable_fields = [
            'date_start',
            'date_end',
            'project_id',
            'department_id',
            'user_id',
            'partner_id',
            'company_id',
        ]
        new_vals = {}
        for field in cascadeable_fields:
            if field in vals:
                new_vals[field] = vals[field]

        if new_vals:
            elements = self.mapped('budget_line_ids') + self.mapped('budget_line_ids.budget_detail_ids') + self.mapped('budget_detail_ids')
            if elements:
                super(BudgetElement, elements).write(new_vals)

        return ret

    
    def unlink(self):
        """
        Authorise unlinking read-only if context allows it
        """
        if not self.env.context.get('allow_readonly'):
            for element in self:
                if element.is_readonly:
                    raise UserError(_('You cannot delete generated budget elements.'))

        invoices = self.env['account.move.line'].search([('budget_element_id', 'in', self.ids)]).mapped('move_id')
        for invoice in invoices:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete budget elements linked to invoices that are not in a draft or cancelled state.'))

        purchases = self.env['purchase.order.line'].search([('budget_element_id', 'in', self.ids)]).mapped('order_id')
        for purchase in purchases:
            if purchase.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete budget elements linked to purchase orders that are not in a draft or cancelled state.'))

        # Remove all budgets linked to this one
        elements = self.mapped('budget_line_ids')
        if elements:
            elements.unlink()

        elements = self.mapped('budget_detail_ids')
        if elements:
            elements.unlink()

        distributions = self.mapped('distribution_cost_ids')
        if distributions:
            distributions.unlink()

        distributions = self.mapped('distribution_budget_ids')
        if distributions:
            distributions.unlink()

        self.mapped('member_ids').unlink()

        super(BudgetElement, self).unlink()

    
    def list_invoices(self):
        """
        List purchases
        """
        self.ensure_one()

        element_ids = self.mapped('budget_line_ids.budget_detail_ids.id') + self.mapped('budget_line_ids.id') + self.mapped('budget_detail_ids.id') + self.mapped('id')

        action = self.env.ref('account.action_move_in_invoice_type', False)
        action_data = action.read()[0]

        move_ids = self.env['account.move.line'].search([('budget_element_id', 'in', element_ids)]).mapped('move_id.id')

        action_data.update(
            context={
                'default_default_budget_element_id': self.id,
                'target': 'new',
            },
            domain=[('id', 'in', move_ids)],
        )
        return action_data

    
    def create_invoice(self):
        """
        Create an empty invoice (supplier) for the budget element
        """
        self.ensure_one()

        action = self.env.ref('account.action_move_in_invoice_type', False)
        action_data = action.read()[0]

        action_data.update(
            views=[(False, u'form'), (False, u'tree')],
            context={
                'default_default_budget_element_id': self.id,
                'default_type': 'in_invoice',
                'type': 'in_invoice',
                'target': 'new',
            }
        )
        return action_data

    
    def list_purchases(self):
        """
        List purchases
        """
        self.ensure_one()

        element_ids = self.mapped('budget_line_ids.budget_detail_ids.id') + self.mapped('budget_line_ids.id') + self.mapped('budget_detail_ids.id') + self.mapped('id')

        action = self.env.ref('purchase.purchase_form_action', False)
        action_data = action.read()[0]

        purchase_order_ids = self.env['purchase.order.line'].search([('budget_element_id', 'in', element_ids)]).mapped('order_id.id')

        action_data.update(
            context={
                'default_default_budget_element_id': self.id,
                'target': 'new',
            },
            domain=[('id', 'in', purchase_order_ids)],
        )
        return action_data

    
    def create_purchase(self):
        """
        Create an empty purchase order for the budget element
        """
        self.ensure_one()

        action = self.env.ref('purchase.purchase_form_action', False)
        action_data = action.read()[0]

        action_data.update(
            views=[(False, u'form'), (False, u'tree')],
            context={
                'default_default_budget_element_id': self.id,
                'target': 'new',
            }
        )
        return action_data

    
    def action_propose_budget(self):
        """
        Set the element and its appropriate lines to 'Proposition'
        """
        elements = self | self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        elements.write({'state': 'proposition'})

    
    def action_open_budget(self):
        """
        Set the element and its appropriate lines to 'Open'
        """
        elements = self | self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        elements.write({'state': 'open', 'was_opened': True, 'copy_initial': False})

    
    def action_close_budget(self):
        """
        Set the element and its appropriate lines to 'Close'
        """
        elements = self | self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        elements.write({'state': 'done'})

    
    def action_cancel_budget(self):
        """
        Set the element and its appropriate lines to 'Cancel'
        """
        elements = self | self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        elements.write({'state': 'cancel'})

    
    def action_redraft_budget(self):
        """
        Set the element and its appropriate lines to 'Draft'
        """
        elements = self | self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        elements.write({'state': 'draft', 'was_opened': False})

    
    def action_uncancel_budget(self):
        """
        Set the element and its appropriate lines to 'Draft'
        """
        elements = self | self.mapped('budget_line_ids') | self.mapped('budget_detail_ids') | self.mapped('budget_line_ids.budget_detail_ids')
        for element in elements:
            if element.was_opened:
                element.write({'state': 'open'})
            else:
                element.write({'state': 'draft'})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
