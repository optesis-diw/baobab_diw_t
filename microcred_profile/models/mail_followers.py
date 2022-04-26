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

from odoo import models, api


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def _add_follower_command(self, res_model, res_ids, partner_data, channel_data, force=True):
        new_partner_data = {}
        user = self.env['res.users']
        for partner_id in partner_data.keys():
            user = user.search([('partner_id', '=', partner_id), ('is_usergroup', '=', True)], limit=1)
            if user:
                partner_ids = user.mapped('user_group_ids.partner_id.id')
                if partner_ids:
                    for new_partner_id in partner_ids:
                        new_partner_data[new_partner_id] = partner_data[partner_id]
            else:
                new_partner_data[partner_id] = partner_data[partner_id]

        return super(MailFollowers, self)._add_follower_command(res_model, res_ids, new_partner_data, channel_data, force=force)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
