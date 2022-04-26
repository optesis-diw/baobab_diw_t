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

from odoo import pooler
import logging
logger = logging.getLogger('microcred_profile')

__name__ = 'Add invoice lines to assets'


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    pool = pooler.get_pool(cr.dbname)
    uid = 1

    asset_obj = pool.get('account.asset')
    asset_ids = asset_obj.search(cr, uid, [('invoice_line_id', '=', False), ('move_id', '!=', False)])
    if asset_ids:
        for asset in asset_obj.browse(cr, uid, asset_ids):
            print asset.id,
            line_ids = []
            for line in asset.move_id.invoice_line_ids:
                if line.price_subtotal == asset.value:
                    line_ids.append(line.id)
            if len(line_ids) == 1:
                print "---->", line_ids[0]
                asset_obj.write(cr, uid, asset.id, {'invoice_line_id': line_ids[0]})
            else:
                print "??????"

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
