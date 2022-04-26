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

from odoo import models, fields, api, _
from collections import defaultdict


class ResPartner(models.Model):
    _inherit = 'res.partner'

    skype = fields.Char(string='Skype', size=64, help='Enter the skype ')
    thirdparty_account = fields.Char(string='Third-party account', size=64, help='Enter the account name of the third-party.')
    contracts_signed = fields.Boolean(string='Contracts signed', help='Check this box if all contracts have been signed.')
    tender_call_done = fields.Boolean(string='Call for tender done', help='Check this box if the call for tender has been done.')
    nda_signed = fields.Boolean(string='NDA signed', help='Check this box if the NDA has been signed.')
    date_signed = fields.Date(string='Contract signed date', help='Enter the date the contract was signed.')
    date_eligibility = fields.Date(string='Eligibility date', help='Enter the eligibility date.')
    dossier_link = fields.Char(string='Dossier link', help='Enter the URL to the supplier\'s dossier.')
    xml_id = fields.Char(string='XML ID', help='The XML ID of this partner.', compute='get_xml_id')
    user_can_view = fields.Boolean(string='User can view', compute='_get_user_can_view', search='_find_user_can_view',)

    
    def _find_user_can_view(self, operator, operand):
        if 'only_company_partners' in self.env.context:
            return [('id', 'in', self.search([('company_id', 'in', (False, self.env.user.company_id.id))]).ids)]
        return [('id', 'in', self.search([]).ids)]

    
    def _get_user_can_view(self):
        """
        Test if the user can view the budget data
        """
        for partner in self:
            partner.user_can_view = (partner.company_id is False or partner.company_id == self.env.user.company_id)

    @api.model
    def create(self, vals):
        """
        Check for auto-subscriptions
        """

        def correct_name(name):
            name = name.lower().replace('.', '_').replace(' ', '_')
            return name

        new_partner = super(ResPartner, self).create(vals)
        partner_ids = self.env['res.users'].sudo().search([('autosubscribe_products', '=', True)]).mapped('user_group_ids.partner_id').ids
        if partner_ids:
            new_partner.sudo().message_subscribe(partner_ids=partner_ids, force=False)

        """
        Create an XML ID as well
        """
        xml_vals = {
            'model': 'res.partner',
            'res_id': new_partner.id,
            'module': '__%s__' % correct_name(self.env.user.company_id.name),
            'name': str(new_partner.id),
        }
        self.env['ir.model.data'].create(xml_vals)

        return new_partner

    
    def get_xml_id(self):
        self.env.cr.execute("""
                            SELECT res_id, module || '.' || name FROM ir_model_data WHERE model = 'res.partner' AND res_id in %(ids)s
                            """, {'ids': tuple(self.ids)})
        res = self.env.cr.fetchall()
        xml_ids = defaultdict(str)
        for line in res:
            xml_ids[line[0]] = line[1]
        for partner in self:
            partner.xml_id = xml_ids[partner.id] or _('<None>')

    
    def _notify(self, message, force_send=False, user_signature=True):
        return super(ResPartner, self._context.get('exclusive_send', self))._notify(message, force_send=force_send, user_signature=user_signature)  # If the context contains an exclusive send, then use the partner list therein defined. Otherwise, proceeed as per usual...

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
