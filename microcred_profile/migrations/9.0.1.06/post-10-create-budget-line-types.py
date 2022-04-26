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

__name__ = 'Create Budget Line Types'


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    pool = pooler.get_pool(cr.dbname)
    uid = 1

    element_obj = pool.get('budget.element')
    line_type_obj = pool.get('budget.line.type')

    element_ids = element_obj.search(cr, uid, [('type', '=', 'budget_line'), ('is_readonly', '=', False)])
    types = {}
    for element in element_obj.browse(cr, uid, element_ids):
        types[element.name] = element.name
        axis_tag_ids = []
        axis_2_name = False
        for tag in element.axis_tag_ids:
            if tag.axis == '2':
                axis_2_name = tag.name
                axis_tag_ids.append(tag.id)
            elif tag.axis == '1':
                axis_tag_ids.append(tag.id)

        if axis_2_name:
            if axis_2_name not in types:
                types[axis_2_name] = line_type_obj.create(cr, uid, {
                    'name': element.name,
                    'company_id': 1,
                    'active': True,
                    'tag_ids': [(6, 0, axis_tag_ids)],
                })
            element_obj.write(cr, uid, element.id, {'budget_line_type_id': types[axis_2_name]})

    search_list = [
        'Gross Salaries',
        'Gross Bonus',
        'Employer contribution',
        'Gross Salaries expat',
        'Gross Bonus expat',
        'Employer contribution expat',
        'Local Gross Salaries+ employer contribution (Group Staff - Hub IT)',
        'VIE',
    ]
    for detail_type in search_list:
        new_type = line_type_obj.create(cr, uid, {
            'name': detail_type,
            'company_id': 1,
            'active': True,
        })
        element_ids = element_obj.search(cr, uid, [('type', '=', 'budget_detail'), ('is_readonly', '=', False), ('name', '=', detail_type)])
        element_obj.write(cr, uid, element_ids, {
            'budget_line_type_id': new_type
        })

    found_list = []
    element_ids = element_obj.search(cr, uid, [('type', '=', 'budget_detail'), ('is_readonly', '=', False), ('name', 'not in', search_list)])
    for element in element_obj.browse(cr, uid, element_ids):
        if element.name not in found_list:
            found_list.append(element.name)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
