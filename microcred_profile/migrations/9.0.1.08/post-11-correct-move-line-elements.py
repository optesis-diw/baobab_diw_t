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

__name__ = 'Correct move line budget elements'


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    pool = pooler.get_pool(cr.dbname)
    uid = 1

    move_line_obj = pool.get('account.move.line')
    invoice_line_obj = pool.get('account.move.line')
    element_obj = pool.get('budget.element')
    distribution_obj = pool.get('budget.element.distribution')

    line_ids = invoice_line_obj.search(cr, uid, [
        ('move_id.move_id', '!=', False),
    ], order="id")
    used_ids = []
    for line_id in line_ids:
        move_line_ids = move_line_obj.search(cr, uid, [
            ('invoice_line_id', '=', line_id)
        ])
        if not move_line_ids:
            # print('Searching for invoice line #%d' % line_id)
            line = invoice_line_obj.browse(cr, uid, line_id)
            domain = [
                ('move_id', '=', line.move_id.id),
                ('id', 'not in', used_ids),
            ]
            direction = 1
            amount = line.price_subtotal
            if line.move_id.type == 'in_refund':
                direction *= -1
            if amount < 0.0:
                direction *= -1
                amount = -amount
            if direction == 1:
                domain.append(['debit', '=', amount])
            else:
                domain.append(['credit', '=', amount])
            move_line_ids = move_line_obj.search(cr, uid, domain)
            if not move_line_ids:
                # print(">>>>>>>>>>>>>> Can't find link for invoice line #%d (invoice #%d)!" % (line_id, line.move_id.id))
                pass
            else:
                if len(move_line_ids) > 1:
                    move_line_ids = [move_line_ids[0]]
                    used_ids.append(move_line_ids[0])

                # print("Linking %d to %d" % (line_id, move_line_ids[0]))
                move_line_obj.write(cr, uid, move_line_ids[0], {'invoice_line_id': line_id})

    # print "Correcting invoice line ids"
    move_line_ids = move_line_obj.search(cr, uid, [('invoice_line_id', '!=', False)], order="id desc")
    # print len(move_line_ids)
    for line in move_line_obj.browse(cr, uid, move_line_ids):
        # print line.id
        move_line_obj.write(cr, uid, line.id, {'budget_element_id': line.invoice_line_id.budget_element_id.id})

    # print "Forcing recalculation"
    new_move_line_ids = move_line_obj.search(cr, uid, [('budget_element_id', '!=', False), ('id', 'not in', move_line_ids)], order="id desc")
    # print len(new_move_line_ids)
    if new_move_line_ids:
        for line in move_line_obj.browse(cr, uid, new_move_line_ids):
            # print line.id
            move_line_obj.write(cr, uid, line.id, {'budget_element_id': line.budget_element_id.id})

    # print "Forcing recalculation #2"
    distribution_ids = distribution_obj.search(cr, uid, [])
    # print len(distribution_ids)
    for distribution in distribution_obj.browse(cr, uid, distribution_ids):
        # print distribution.id
        distribution_obj.write(cr, uid, distribution.id, {'parent_id': distribution.parent_id.id})

    element_ids = element_obj.search(cr, uid, [])
    for element in element_obj.browse(cr, uid, element_ids):
        print('%d\t%s\t%d\t%.2f\t%s\t%s\t%d' % (element.id, element.type_id.name, element.budget_id.id, element.amount_invoiced, repr(element.budget_line_ids.ids), repr(element.budget_detail_ids.ids), element.linked_distribution_id.parent_id or 0))
        pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
