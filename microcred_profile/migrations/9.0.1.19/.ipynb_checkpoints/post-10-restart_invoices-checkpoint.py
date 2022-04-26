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

__name__ = 'Recalculate budget'


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
        bad_invoices = env['account.move'].search([('reference', 'in', ('1', '42478')), ('microcred_state', 'in', ('paid', 'cancel'))])
        for invoice in bad_invoices:
            invoice.reference = invoice.reference + ' (' + invoice.state + ')'

        valid_invoices = env['account.move'].search([('state', 'in', ('validated', 'draft'))])
        valid_invoices = env['account.move']

        for invoice in valid_invoices:
            write = {
                'state': 'draft',
                'microcred_state': 'draft',
                # 'was_validated': True
            }
            write.update(invoice.set_required_flags())
            invoice.write(write)
            invoice.delete_workflow()
            invoice.create_workflow()

        open_invoices = env['account.move'].search([('microcred_state', '=', 'open')])
        open_invoices = env['account.move']
        open_invoices.write({'was_validated': True})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
