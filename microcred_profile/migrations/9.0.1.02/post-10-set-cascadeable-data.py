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

__name__ = 'Corrected cascaded deletions'


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    pool = pooler.get_pool(cr.dbname)
    uid = 1

    element_obj = pool.get('budget.element')
    element_ids = element_obj.search(cr, uid, [('type_id.type', 'in', ('budget_line', 'budget_detail')), ('budget_id', '=', False)])
    element_obj.unlink(cr, uid, element_ids, context={'allow_readonly': True})
    element_ids = element_obj.search(cr, uid, [('type_id.type', 'in', ('budget_line', 'budget_detail')), ('is_readonly', '=', True), ('linked_distribution_id', '!=', False)])
    to_delete_ids = []
    for element in element_obj.browse(cr, uid, element_ids):
        print element.id, element.linked_distribution_id.id, element.linked_distribution_id.parent_id.id
        if element.linked_distribution_id and not element.linked_distribution_id.parent_id:
            to_delete_ids.append(element.linked_distribution_id.id)
    pool.get('budget.element.distribution').unlink(cr, uid, to_delete_ids, context={'allow_readonly': True})
    #element_ids = element_obj.search(cr, uid, [('type_id.type', 'in', ('budget_line', 'budget_detail')), ('is_readonly', '=', True), ('linked_budget_distribution_id', '=', False)])
    element_ids = element_obj.search(cr, uid, [('type_id.type', '=', 'budget_detail')])
    to_delete_ids = []
    for element in element_obj.browse(cr, uid, element_ids):
        if element.budget_id.type != 'budget_line':
            # Needs to be deleted
            to_delete_ids.append(element.id)
    element_obj.unlink(cr, uid, to_delete_ids, context={'allow_readonly': True})


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
