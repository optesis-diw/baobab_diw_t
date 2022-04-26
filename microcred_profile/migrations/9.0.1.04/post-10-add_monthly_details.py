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

__name__ = 'Add budget period details'


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    pool = pooler.get_pool(cr.dbname)
    uid = 1

    element_obj = pool.get('budget.element')
    element_ids = element_obj.search(cr, uid, [('date_end', '!=', False), ('date_start', '!=', False)])
    element_obj.add_period_detail(cr, uid, element_ids)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
