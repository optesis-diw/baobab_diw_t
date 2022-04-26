# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Chris TRIBBECK <chris.tribbeck@syleam.fr>
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

from odoo import SUPERUSER_ID, api
import logging
logger = logging.getLogger('Set budget element subtypes')


def migrate(cr, v):
    with api.Environment.manage():
        uid = SUPERUSER_ID
        ctx = api.Environment(cr, uid, {})['res.users'].context_get()
        env = api.Environment(cr, uid, ctx)
        budget_elements = env['budget.element'].search([('budget_id', '=', False), ('child_budget_ids', '!=', False)])
        for element in budget_elements:
            tag_3 = False
            for tag in element.axis_tag_ids:
                if tag.axis == '3':
                    tag_3 = tag.id

            if tag_3:
                child_ids = element.child_budget_ids
                while child_ids:
                    for child in child_ids:
                        copy_3 = True
                        for tag in child.axis_tag_ids:
                            if tag.axis == '3' and tag.id != tag_3:
                                copy_3 = False
                                break

                        if copy_3:
                            new_list = [tag_3]
                            for tag in child.axis_tag_ids:
                                if tag.axis != '3':
                                    new_list.append(tag.id)
                            child.write({'axis_tag_ids': [(6, 0, new_list)]})
                    child_ids = child_ids.mapped('child_budget_ids')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
