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

from odoo import models, fields, api, _


class AccountAxis(models.Model):
    _name = 'account.axis'
    _inherit = 'mail.thread'
    _description = 'Account axis definition'
    _order = 'company_id, number, name'
    _sql_constraints = [
        ('name_unique', 'unique (name,company_id)', 'The name must be unique for this company!'),
        ('number_unique', 'unique (number,company_id)', 'The number must be unique for this company!'),
    ]

    name = fields.Char(string='Name',  required=True, help='The name of the axis', translate=True)
    number = fields.Integer(string='Axis number', required=True, help='Select the axis number.')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', help='Select the company.', copy=False)
    axis_type = fields.Selection(selection=[('mono', 'Mono-tag'), ('single', 'Single per group'), ('multi', 'Multi-tag')],
                                 required=True, default='mono', string='budget axis Type', help='Select the axis type.')
    rule_ids = fields.One2many(comodel_name='account.axis.rule', inverse_name='axis_id', string='Rules',
                               help='Add visibility rules.', copy=True)
    value_ids = fields.One2many(comodel_name='account.axis.tag', inverse_name='axis_id', string='Possible values',
                                help='Enter the possible values.', copy=True)
    sage_export = fields.Boolean(string='Export SAGE', help='Check this box if you want to export this axis to SAGE.')
    reinvoice = fields.Boolean(string='Reinvoice', help='Check this box if this axis is used for reinvoicing.')
    budget_split = fields.Boolean(string='Budget split', help='Check this box if this axis is to be split to child budgets on sage exports.')
    export_reverse = fields.Boolean(string='Reverse in SAGE export', help='Check this box if the other of the groups are to be inversed in SAGE exports.')

    
    def copy(self, default):
        if 'name' not in default:
            default['name'] = self.name + _(' (copy)')
        return super(AccountAxis, self).copy(default)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
