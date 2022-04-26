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

__name__ = ''


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    pool = pooler.get_pool(cr.dbname)
    uid = 1

    model_obj = pool.get('ir.model')
    rule_obj = pool.get('ir.rule')

    model_ids = model_obj.search(cr, uid, [('model', 'in', (
        'account.tax',
        'account.journal',
        'account.move',
        'account.move.line',
        'account.fiscal.policy',
        'account.account',
        'account.move.line',
        'account.asset',
        'account.asset',
        'purchase.order',
        'purchase.order.line',
        'account.payment',
    ))])
    rule_ids = rule_obj.search(cr, uid, [
        ('model_id', 'in', model_ids),
        ('domain_force', '=', "['|',('company_id','=',False),('company_id','child_of',[user.company_id.id])]"),
    ])
    rule_obj.write(cr, uid, rule_ids, {'domain_force': "['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]"})

    """
    ['|',('company_id','=',False),('company_id','child_of',[user.company_id.id])]
    ['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]
    """

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
