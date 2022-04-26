# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr/>)
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

from odoo import models, api, fields


class AccountAssetCategory(models.Model):
    #_name = 'account.depreciation.asset'
    _inherit = 'account.asset'

    is_accrued_expense = fields.Boolean(string='Accrued expenses', help='If checked, this is accrued expenses.', default=False)
    daily_prorata = fields.Boolean(string='Daily Prorata', help='Check if the prorata amount is to be calculated on a daily basis.')
    end_of_month = fields.Boolean(string='End of month', help='Generate movements at the end of the month.')
    double_entry = fields.Boolean(string='Double entry', help='Check this box if 2 journal entries are to be used.')

    @api.onchange('is_accrued_expense')
    def onchange_accrued_expense(self):
        if self.is_accrued_expense:
            self.prorata = True
            self.method_number = 10
            self.daily_prorata = True

    @api.model
    def create(self, values):
        if (values.get('is_accrued_expense', False) or self.env.context.get('default_is_accrued_expense', False)) and not values.get('account_asset_id', False):
            values['account_asset_id'] = values['account_depreciation_id']
        return super(AccountAssetCategory, self).create(values)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
