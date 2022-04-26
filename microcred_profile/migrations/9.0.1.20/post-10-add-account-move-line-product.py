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

__name__ = 'Correct move lines'


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
        for company in env['res.company'].search([]):
            move_lines = env['account.move.line'].search([('distribution_partner_ids', '!=', False), ('budget_element_id', '!=', False), ('product_id', '=', False), ('company_id', '=', company.id),
                                                         ('id', 'not in', (0, 30439))])
            for line in move_lines:
                print line.id
                line.write({
                    'product_id': company.default_expensify_product_id.id
                })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
