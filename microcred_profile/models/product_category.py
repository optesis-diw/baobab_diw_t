# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
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

from odoo import models, fields


class productCategory(models.Model):
    _inherit = 'product.category'

    analytic_axis_id = fields.Many2one(comodel_name='account.analytic.tag', string='Analytic Axis', domain=[('axis', '=', '2')], deprecated=True)
    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' Axis tags13', help='This contains the axis tags for this invoice.')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
