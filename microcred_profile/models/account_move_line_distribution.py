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


class AccountMoveLineDistribution(models.Model):
    _name = 'account.move.line.distribution'
    _description = 'Account move line distribution'

    move_line_id = fields.Many2one('account.move.line', string='Move line', help='The move line', required=True )
    amount_fixed = fields.Float(string='Fixed amount', digits=("Account"), help='Enter the fixed amount.')
    budget_partner_id = fields.Many2one('budget.element', string='Budget partner', help='Budget partner', required=True, )
    reinvoice_batch_id = fields.Many2one('budget.reinvoice.batch', string='Renvoiced batch', help='The batch executed using this move line.')
    reinvoice_invoice_line_id = fields.Many2one('account.move.line', string='Renvoiced invoice line', help='The invoice_line linked to this move line.')
    asset_line_id = fields.Many2one('account.asset', string='Depreciation Line', help='The depreciation linked to this distribution (if any).')

    



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
