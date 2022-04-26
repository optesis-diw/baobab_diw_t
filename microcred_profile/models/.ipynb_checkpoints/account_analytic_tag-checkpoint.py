# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Yannis Pou-Vich <yannis.pouvich@syleam.fr>
#
#    This file is a part of microcred_profile
#
#    microcred_profile is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    microcred_profile is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models


class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"
    _order = 'axis, name'

    axis = fields.Selection(selection=[
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4A', '4A'),
        ('4B', '4B'),
    ], string='Axis', help='')
    invoice_type = fields.Selection(selection=[
        ('customer', 'Customer'),
        ('supplier', 'Supplier')
    ], string='Invoice Type')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
