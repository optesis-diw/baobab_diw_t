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


class BudgetElementType(models.Model):
    _inherit = "budget.element.type"

    #migration by Yowit optesis ctd
    #axis_1 = fields.Boolean(string='Axis 1', default=False, required=True, )
    #axis_2 = fields.Boolean(string='Axis 2', default=False, required=True, )
    #axis_3 = fields.Boolean(string='Axis 3', default=False, required=True, )
    #axis_4 = fields.Boolean(string='Axis 4', default=False, required=True, )
    axis_1 = fields.Boolean(string='Axis 1', default=False, required=False )
    axis_2 = fields.Boolean(string='Axis 2', default=False, required=False)
    axis_3 = fields.Boolean(string='Axis 3', default=False, required=False)
    axis_4 = fields.Boolean(string='Axis 4', default=False, required=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
