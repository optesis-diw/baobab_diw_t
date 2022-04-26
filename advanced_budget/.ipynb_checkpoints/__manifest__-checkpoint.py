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

{
    'name': 'Advanced Budget',
    'version': '14.01',
    'category': 'Custom',
    'description': """Advanced budget""",
    'author': 'SYLEAM',
    'website': 'http://www.syleam.fr/',
    'depends': [
        'mail',
        'account',
        'purchase',
        'sale',
        'hr',
        'hr_timesheet',
        'project',
        'hr_expense',
    ],
    'data': [
        'data/budget_element_types.xml',
        'wizard/add_budget_details.xml',
        'wizard/add_budget_distribution.xml',
        'wizard/modify_amount.xml',

        'views/budget_element.xml',
        'views/purchase_order.xml',
        'views/account_invoice.xml',
        'views/sale_order.xml',
        #'security/groups.xml',
        'security/ir.model.access.csv',
        #'view/menu.xml',
        #'wizard/wizard.xml',
        #'report/report.xml',
    ],
    #'external_dependancies': {'python': ['kombu'], 'bin': ['which']},
    'installable': True,
    'active': False,
    'license': 'AGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
