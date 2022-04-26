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
from odoo.exceptions import ValidationError


class BudgetLineType(models.Model):
    _name = 'budget.line.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Budget line type'
    _order = 'name'

    name = fields.Char(string='Name', size=64, tracking=True, help='Enter the name of this budget line type.')
    company_id = fields.Many2one('res.company', string='Company',tracking=True, help='Select the compant to whom this type is associated.')
    account_ids = fields.One2many('account.account', 'budget_line_type_id', string='Accounts', tracking=True,
                                  help='Select the account(s) linked to this type (uses in data import).')
    active = fields.Boolean(string='Active', help='If checked, this budget line type is active.', default=True)
    tag_ids = fields.Many2many(comodel_name='account.analytic.tag',tracking=True, string=' Axis tags25 for the budget element', help='This contains the axis tags for this budget element.')
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags26',tracking=True, help='This contains the axis tags for this purchase line.')
    parent_id = fields.Many2one(comodel_name='budget.line.type', string='Parent', help='The parent budget line type.')
    child_ids = fields.One2many(comodel_name='budget.line.type', inverse_name='parent_id',tracking=True, string='Children', help='The sub line types of this line type.')
    sequence = fields.Integer(string=' line Sequence', help='The sequence of the line types.', default=100)
    full_sequence = fields.Integer(string=' check Sequence', help='The sequence of the line types.', store=True, compute='_compute_full_sequence')
    user_can_modify = fields.Boolean(string='User can view', compute='_get_user_can_view', )


    @api.constrains('parent_id', 'child_ids')
    def constrain_parent(self):
        if self.parent_id and len(self.child_ids) > 0:
            raise ValidationError(_('You cannot define more than two levels of budget line types.'))

    @api.depends('sequence', 'parent_id')
    def _compute_full_sequence(self):
        for line_type in self:
            if not line_type.parent_id:
                line_type.full_sequence = 10000 * line_type.sequence
            else:
                line_type.full_sequence = line_type.sequence
                
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
