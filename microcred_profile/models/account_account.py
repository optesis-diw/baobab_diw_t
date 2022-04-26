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

from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    budget_line_type_id = fields.Many2one('budget.line.type', string='Budget line type', help='The budget line type to which this account is linked during imports.')
    compensation_payroll_id = fields.Many2one('account.account', string='Payroll compensation account', help='Select the compensation account used in payroll imports.')
    export_thirdparty_account = fields.Boolean(string='Export third-party account', help='If checked, the SAGE export will add the third-party account with this account\'s journal items.')
    authorise_analytics = fields.Boolean(string='Authorise Analytics', help='If checked, the analytical data will be implemented for journal items using this account.')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
