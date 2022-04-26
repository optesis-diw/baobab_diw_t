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

from odoo import models, api, fields
from odoo import fields
from odoo import SUPERUSER_ID


class ResUsers(models.Model):
    _inherit = 'res.users'

    # TODO : Add the correct rights

    def _is_share(self, cr, uid, ids, name, args, context=None):
        res = {}
        for user in self.browse(cr, uid, ids, context=context):
            res[user.id] = self.has_group(cr, user.id, 'base.group_portal')

        return res

    # TODO : Add the correct rights

    def _store_trigger_share_res_groups(self, cr, uid, ids, context=None):
        group_user = self.pool['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'base.group_portal', context=context)
        if group_user and group_user.id in ids:
            return group_user.users.ids
        return []

    is_usergroup = fields.Boolean(string='Is usergroup', help='Check this box if the user is a user group.')
    user_group_ids = fields.Many2many('res.users', relation='res_users_usergroups_rel', column1='user_id', column2='group_id', string='Users in this group', help='The users in this group.')
    autosubscribe_budgets = fields.Boolean(string='Auto-subscribe budgets', help='Check this box if the user or this group be automatically subscribed to all budgets.')
    autosubscribe_invoices = fields.Boolean(string='Auto-subscribe invoices', help='Check this box if the user or this group be automatically subscribed to all invoices.')
    autosubscribe_purchases = fields.Boolean(string='Auto-subscribe purchases', help='Check this box if the user or this group be automatically subscribed to all purchases.')
    autosubscribe_partners = fields.Boolean(string='Auto-subscribe partners', help='Check this box if the user or this group be automatically subscribed to all partners.')
    autosubscribe_products = fields.Boolean(string='Auto-subscribe products', help='Check this box if the user or this group be automatically subscribed to all products.')
    # TODO : Add the correct rights
    #_columns = {
    #    'share': fields.(_is_share, string='Share User', type='boolean',
    #                                 store={
    #                                     'res.users': (lambda self, cr, uid, ids, c={}: ids, ['groups_id'], 60),
    #                                     'res.users': (lambda self, cr, uid, ids, c={}: ids, ['groups_id'], 60),
     #                                    'res.groups': (_store_trigger_share_res_groups, ['users'], 60),
     #                                }, help="External user with limited access, created only for the purpose of sharing data."),
   # }
    # share = fields.Boolean(string='Shared', help='Is shared', store=True, compute='_get_shared', )

    # 
    # @api.depends('groups_id')
    # def _get_shared(self):
    #     group_id = self.env.ref('base.group_portal')
    #     for user in self:
    #         user.share = group_id in user.groups_id
#     @api.model
#     def default_get(self, fields_list):
#         """
#         Get the max and min dates
#         """

#         values = super(ResUsers, self).default_get(fields_list)

#         values['sel_groups_1_9_10'] = True

#         return values

    @api.onchange('is_usergroup')
    def clear_usergroups(self):
        """
        Clear the user group's users or the user's usergroups
        """
        self.user_group_ids = False

    # base.group_portal

#     @api.model
#     def create(self, values):
#         """
#         Add base.group_portal to the list of groups if the user is a usergroup
#         """
#         if values.get('is_usergroup'):
#             portal_groups = self.env['res.groups'].search([('is_portal', '=', True)]).ids
#             for group in portal_groups:
#                 values['in_group_%d' % group] = True
#         return super(ResUsers, self).create(values)

    
#     def write(self, values):
#         """
#         Add base.group_portal to the list of groups if the user is a usergroup
#         """
#         if values.get('is_usergroup'):
#             portal_groups = self.env['res.groups'].search([('is_portal', '=', True)]).ids
#             for group in portal_groups:
#                 values['sel_groups_%d' % group] = True
#         return super(ResUsers, self).write(values)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
