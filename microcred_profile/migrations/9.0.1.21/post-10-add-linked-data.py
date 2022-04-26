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

from odoo import SUPERUSER_ID, api
import logging
logger = logging.getLogger('microcred_profile')

__name__ = 'Linked elements data'


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    with api.Environment.manage():
        uid = SUPERUSER_ID
        ctx = api.Environment(cr, uid, {})['res.users'].context_get()
        env = api.Environment(cr, uid, ctx)
        # Reset all valid invoices
        for distribution in env['budget.element.distribution'].search([]):
            update_write = {}
            if distribution.parent_id.budget_line_type_id:
                update_write.update({
                    'budget_line_type_id': distribution.parent_id.budget_line_type_id.id,
                })

            if distribution.parent_id.subtype_id.id:
                update_write.update({
                    'subtype_id': distribution.parent_id.subtype_id.id,
                })

            if distribution.parent_id.all_tag_ids:
                update_write.update({
                    'all_tag_ids': [(6, 0, [x.id for x in distribution.parent_id.all_tag_ids])],
                })

            if update_write:
                distribution.linked_budget_line_ids.write(update_write)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
