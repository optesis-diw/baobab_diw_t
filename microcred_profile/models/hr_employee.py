# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 Syleam (<http://www.syleam.fr/>)
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
import odoo.addons.decimal_precision as dp


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    timesheet_price = fields.Float(string='Sales price', digits=("Account"), help='Enter the sales price of this employee.')

    @api.model
    def create(self, vals):
        new_employee = super(HrEmployee, self).create(vals)
        if not new_employee.address_id or new_employee.address_id == new_employee.company_id.partner_id:
            new_employee.address_id = new_employee.company_id.partner_id.copy(default={
                'name': vals['name'],
                'parent_id': new_employee.company_id.partner_id.id,
                'is_company': False,
                'company_type': 'person',
                'supplier': True
            })
            new_employee.address_id.name = vals['name']
        return new_employee


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
