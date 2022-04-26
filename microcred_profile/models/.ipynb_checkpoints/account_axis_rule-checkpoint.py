# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.syleam.fr/>)
#              Chris Tribbeck <chris.tribbeck@syleam.fr>
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


class AccountAxisRule(models.Model):
    _name = 'account.axis.rule'
    _description = 'Account axis rule'
    _sql_constraints = [
        ('name_unique', 'unique (axis_id,model_id, subtype)', 'You cannot have multiple rules for the same model, axis and subtype!'),
    ]

    axis_id = fields.Many2one(comodel_name='account.axis', string='Axis', required=True, help='Select the axis.')
    model_id = fields.Many2one(comodel_name='ir.model', string='Model', help='Select the model.')
    application = fields.Selection(selection=[('optional', 'Optional'), ('required', 'Required')], required=True,
                                   default='optional', string='Application', help='Select how the axis is to be viewed.')
    subtype = fields.Char(string='axis Subtype',  help='Enter any subtype data.')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
