# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Yannis Pou-Vich <yannis.pouvich@syleam.fr>
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

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    analytic_axis_id = fields.Many2one(comodel_name='account.analytic.tag', string='Analytic Axis', domain=[('axis', '=', '2')], help='', deprecated=True)
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags14', help='This contains the axis tags for this invoice.')
    user_can_view = fields.Boolean(string='User can view', compute='_get_user_can_view', search='_find_user_can_view',)

    
    def _find_user_can_view(self, operator, operand):
        if 'only_company_products' in self.env.context:
            return [('id', 'in', self.search([('company_id', 'in', (False, self.env.user.company_id.id))]).ids)]
        return [('id', 'in', self.search([]).ids)]

    
    def _get_user_can_view(self):
        """
        Test if the user can view the budget data
        """
        for product in self:
            product.user_can_view = (product.company_id is False or product.company_id == self.env.user.company_id)

    @api.model
    def create(self, vals):
        """
        Check for auto-subscriptions
        """
        new_product = super(ProductTemplate, self).create(vals)
        partner_ids = self.env['res.users'].sudo().search([('autosubscribe_products', '=', True)]).mapped('user_group_ids.partner_id').ids
        if partner_ids:
            new_product.sudo().message_subscribe(partner_ids=partner_ids, force=False)

        return new_product


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
