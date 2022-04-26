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

from odoo import models, api, fields


class WizardChangeAccountTagsLine(models.TransientModel):
    _name = "wizard.change.account.tags.line"
    _description = "Change Account Tags line"
    _order = "number"

    wizard_id = fields.Many2one(comodel_name='wizard.change.account.tags', string='Wizard')
    axis_id = fields.Many2one(comodel_name='account.axis', string='Axis', required=True, readonly=True, help='Select the axis.')
    application = fields.Selection(selection=[('optional', 'Optional'), ('required', 'Required')], readonly=True)
    tag_ids = fields.Many2many(comodel_name='account.axis.tag', string='line Tags account', help='Select the tag(s).')
    number = fields.Integer(string='Axis number', required=True, help='Select the axis number.', readonly=True)
    error = fields.Selection(selection=[
        ('required', 'A value is required'),
        ('mono', 'You can only have one value'),
        ('single', 'You can only have 1 of each subgroup')
    ], string='Error', readonly=True)
    in_error = fields.Boolean(string='In error')

#     @api.model
#     def get_error_message(self, tag_ids, application, axis_type):
#         error = False
#         if not tag_ids and application == 'required':
#             error = 'required'
#         elif len(tag_ids) > 1 and axis_type == 'mono':
#             error = 'mono'
#         elif len(tag_ids) > 1 and axis_type == 'single':
#             subgroup_found = {}
#             for tag in tag_ids:
#                 if tag.subgroup in subgroup_found:
#                     error = 'single'
#                     break
#                 subgroup_found[tag.subgroup] = True

#         return error

#     @api.onchange('tag_ids')
#     def onchange_tag_ids(self):
#         error = self.get_error_message(self.tag_ids, self.application, self.axis_id.axis_type)

#         self.update({
#             'in_error': (error is not False),
#             'error': error
#         })


class WizardChangeAccountTags(models.TransientModel):
    _name = "wizard.change.account.tags"
    _description = "Change Account Tags"

    line_ids = fields.One2many(comodel_name='wizard.change.account.tags.line', inverse_name='wizard_id', string='Axes', help='Enter the axes.')
    move_line_id = fields.Many2one(comodel_name='account.move.line', string='Account Move Line')
    analytic_line_id = fields.Many2one(comodel_name='account.analytic.line', string='Account Analytic Line')
    budget_element_id = fields.Many2one('budget.element', string='Budget element')
    purchase_id = fields.Many2one('purchase.order', string='Purchase order')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase order line')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice line')
    move_id = fields.Many2one('account.move', string='Invoice')
    asset_line_id = fields.Many2one('account.asset', string='Depreciation_line')
    line_type_id = fields.Many2one('budget.line.type', string='Budget line type')
    product_category_id = fields.Many2one(comodel_name='product.category', string='Product category')
    product_template_id = fields.Many2one(comodel_name='product.template', string='Product template')
    all_ok = fields.Boolean(string='All ok', readonly=True)

    @api.onchange('line_ids')
    def onchange_line_ids(self):
        for line in self.line_ids:
            if line.in_error:
                self.all_ok = False
                return

        self.all_ok = True

    @api.model
    def default_get(self, fields_list):
        """
        Return account tags information
        """
        values = super(WizardChangeAccountTags, self).default_get(fields_list)
        line = False
        model_name = self.env.context.get('active_model')
        model_subtype = False
        company = False

        if model_name == 'account.move.line':
            values['move_line_id'] = self.env.context.get('active_id')
            line = self.env['account.move.line'].browse(values['move_line_id'])
            company = line.company_id
        elif model_name == 'account.asset':
            values['asset_line_id'] = self.env.context.get('active_id')
            line = self.env['account.asset'].browse(values['asset_line_id'])
            company = line.asset.company_id
        elif model_name == 'account.analytic.line':
            values['analytic_line_id'] = self.env.context.get('active_id')
            company = line.company_id
        elif model_name == 'account.move':
            values['move_id'] = self.env.context.get('active_id')
            line = self.env['account.move'].browse(values['move_id'])
            company = line.company_id
        elif model_name == 'account.move.line':
            values['invoice_line_id'] = self.env.context.get('active_id')
            line = self.env['account.move.line'].browse(values['invoice_line_id'])
            company = line.move_id.company_id
        elif model_name == 'purchase.order.line':
            values['purchase_line_id'] = self.env.context.get('active_id')
            line = self.env['purchase.order.line'].browse(values['purchase_line_id'])
            company = line.company_id
        elif model_name == 'purchase.order':
            values['purchase_id'] = self.env.context.get('active_id')
            line = self.env['purchase.order'].browse(values['purchase_id'])
            company = line.company_id
        elif model_name == 'budget.line.type':
            values['line_type_id'] = self.env.context.get('active_id')
            line = self.env['budget.line.type'].browse(values['line_type_id'])
            company = line.company_id
        elif model_name == 'budget.element':
            values['budget_element_id'] = self.env.context.get('active_id')
            line = self.env['budget.element'].browse(values['budget_element_id'])
            company = line.company_id
            model_subtype = line.type_id.type
        elif model_name == 'product.category':
            values['product_category_id'] = self.env.context.get('active_id')
            line = self.env['product.category'].browse(values['product_category_id'])
            company = self.env.user.company_id
        elif model_name == 'product.template':
            values['product_template_id'] = self.env.context.get('active_id')
            line = self.env['product.template'].browse(values['product_template_id'])
            company = self.env.user.company_id
        elif model_name == 'product.product':
            line = self.env['product.product'].browse(self.env.context.get('active_id')).product_tmpl_id
            values['product_template_id'] = line.id
            company = self.env.user.company_id
        else:
            return values

        if model_name:
            model = self.env['ir.model'].search([('model', '=', model_name)])
            model.ensure_one()
            axis_rules = self.env['account.axis.rule'].search([('model_id', '=', model.id), ('axis_id.company_id', '=', company.id), ('subtype', '=', model_subtype)])

            axis_lines = []
            WizardLine = self.env['wizard.change.account.tags.line']
            for axis_rule in axis_rules:
                axis_line_data = {
                    'axis_id': axis_rule.axis_id.id,
                    'application': axis_rule.application,
                    'number': axis_rule.axis_id.number,
                }
                tags = line.all_tag_ids.filtered(lambda r: r.axis_id == axis_rule.axis_id)
#                 error = WizardLine.get_error_message(tags, axis_rule.application, axis_rule.axis_id.axis_type)
#                 if error:
#                     axis_line_data.update({
#                         'error': error,
#                         'in_error': True
#                     })
                if tags:
                    axis_line_data['tag_ids'] = [(6, 0, [r.id for r in tags])]
                axis_lines.append((0, 0, axis_line_data))

            values['line_ids'] = axis_lines
        return values

    
    def validate(self):
        self.ensure_one()

        data_line = self.move_line_id or\
            self.asset_line_id or\
            self.analytic_line_id or\
            self.purchase_line_id or\
            self.purchase_id or\
            self.invoice_line_id or\
            self.move_id or\
            self.line_type_id or\
            False

        new_tags = self.env['account.axis.tag']
        for line in self.line_ids:
            if line.tag_ids:
                new_tags |= line.tag_ids

        if data_line:
            data_line.write({'all_tag_ids': [(6, 0, new_tags.ids)]})
        elif self.product_category_id or self.product_template_id:
            # Remove the tags for the company and add the new ones
            line = self.product_category_id or self.product_template_id
            tag_changes = []
            for tag in line.all_tag_ids.filtered(lambda r: r.axis_id.company_id == self.env.user.company_id):
                tag_changes = [(3, tag.id)]
            for tag in new_tags:
                tag_changes = [(4, tag.id)]
            if tag_changes:
                line.all_tag_ids = tag_changes
        elif self.budget_element_id:
            old_tags = self.budget_element_id.all_tag_ids
            self.budget_element_id.write({'all_tag_ids': [(6, 0, new_tags.ids)]})
            if old_tags:
                change_new_tags = {}
                change_old_tags = {}
                child_ids = self.budget_element_id.child_budget_ids
                if child_ids:
                    axes = self.env['account.axis'].search([('company_id', '=', self.budget_element_id.company_id.id)])
                    for line in self.line_ids:
                        old_tag = old_tags.filtered(lambda r: r.axis_id == line.axis_id)
                        new_tag = new_tags.filtered(lambda r: r.axis_id == line.axis_id)
                        if sorted(old_tag.ids) != sorted(new_tag.ids):
                            # These have changed - log them into the list of changes to test
                            change_new_tags[line.axis_id] = new_tag
                            change_old_tags[line.axis_id] = old_tag

                    while child_ids:
                        for child in child_ids:
                            child_tags = self.env['account.axis.tag']
                            for axis in axes:
                                these_tags = child.all_tag_ids.filtered(lambda r: r.axis_id == axis)
                                if axis in change_new_tags:
                                    if sorted(change_old_tags[axis].ids) == sorted(these_tags.ids):
                                        child_tags |= change_new_tags[axis]
                                    else:
                                        child_tags |= these_tags
                                else:
                                    # These were not concerned by a change
                                    child_tags |= these_tags

                            child.write({'all_tag_ids': [(6, 0, child_tags.ids)]})
                        child_ids = child_ids.mapped('child_budget_ids')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
