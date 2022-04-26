# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Chris TRIBBECK <chris.tribbeck@syleam.fr>
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

from odoo import SUPERUSER_ID, api
import logging
logger = logging.getLogger('Set budget element subtypes')


def migrate(cr, v):
    with api.Environment.manage():
        uid = SUPERUSER_ID
        ctx = api.Environment(cr, uid, {})['res.users'].context_get()
        env = api.Environment(cr, uid, ctx)
        companies = env['res.company'].search([])
        for company in companies:
            account_moves = env['account.move.line'].search([('company_id', '=', company.id), ('currency_id', '!=', company.currency_id.id), ('distribution_partner_ids', '!=', False)])
            if account_moves:
                for line in account_moves:
                    rate = line.currency_id.with_context({'company_id': line.company_id.id, 'date': line.date}).rate
                    for distribution in line.distribution_partner_ids:
                        distribution.amount_fixed = distribution.amount_fixed / rate

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
