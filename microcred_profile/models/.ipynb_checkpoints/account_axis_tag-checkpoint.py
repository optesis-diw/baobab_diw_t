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

from odoo import models, fields, api


class AccountAxisTag(models.Model):
    _name = 'account.axis.tag'
    _description = 'Account axis tag'

    _sql_constraints = [
        ('name_unique', 'unique (axis_id,name,subgroup)', 'You cannot have multiple rules for the same axis, name and subgroup!'),
    ]

    axis_id = fields.Many2one(comodel_name='account.axis', string='Axis', required=True, help='The axis.')
    name = fields.Char(string='Tag name',  index=True, required=True)
    extra_data = fields.Char(string='Extra data',  help='Any extra data')
    subgroup = fields.Char(string='Group', size=1, help='Enter the group.')
    color = fields.Integer('Color Index')

    
    def get_company_equivalent(self, company_id):
        self.ensure_one()
        if self.axis_id.company_id == company_id:
            return self

        return self.search([('name', '=', self.name), ('axis_id.company_id', '=', company_id.id), ('axis_id.number', '=', self.axis_id.number)])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
