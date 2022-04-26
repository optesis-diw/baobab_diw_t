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

from odoo import models, api, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp


class ResCompany(models.Model):
    _inherit = ['res.company', 'mail.thread']
    _name = 'res.company'

    period_ids = fields.One2many('account.period', 'company_id', string='Periods', help='The periods.')
    po_double_validation = fields.Selection(selection_add=[('three_step', 'Get 3 levels of approvals to confirm a purchase order')])
    po_triple_validation_amount = fields.Monetary(string='Triple validation amount', default=5000)
    invoice_validation_department_amount = fields.Monetary(string='Department validation after', default=5000)
    invoice_validation_cost_control_amount = fields.Monetary(string='Cost control validation after', default=7500)
    invoice_validation_head_finance_amount = fields.Monetary(string='Head finance validation after', default=10000)
    distribution_required = fields.Boolean(string='Invoice distribution required', help='Check this box if the cost distribution is required on invoice validation.')
    default_expensify_product_id = fields.Many2one(comodel_name='product.product', string='Default expensify product', help='Select the default expensify product.')
    default_transfer_charge = fields.Float(string='Default transfer charge', digits=("Account"), help='Enter the default transfer charge with respect to the holding (Microcred S.A.S.).')

    
    def create_2_year_periods(self):
        self.create_monthly_periods()

    
    def create_monthly_periods(self, from_date=None, number=24):
        period_obj = self.env['account.period']
        for company in self:
            if not from_date:
                cur_date = datetime.today() + relativedelta(days=15) + relativedelta(day=1) + relativedelta(month=1)
            else:
                cur_date = datetime.strptime(from_date, '%Y-%m-%d') + relativedelta(day=1)
            new_periods = []
            for month in range(number):
                date_start = cur_date.strftime('%Y-%m-%d')
                date_end = (cur_date + relativedelta(days=40) + relativedelta(day=1) + relativedelta(days=-1)).strftime('%Y-%m-%d')
                cur_date = cur_date + relativedelta(days=40) + relativedelta(day=1)
                if not period_obj.search([('date_start', '=', date_start), ('company_id', '=', company.id)]):  # The period wasn't found - create it
                    new_periods.append((0, 0, {
                        'date_start': date_start,
                        'date_end': date_end
                    }))

            if new_periods:
                company.write({'period_ids': new_periods})

    
    def fully_close_next_period(self):
        period_obj = self.env['account.period']
        for company in self:
            next_period = period_obj.search([
                ('date_end', '>', company.fiscalyear_lock_date),
                ('state', '!=', 'fully_closed'),
                ('company_id', '=', company.id),
            ], limit=1, order='date_end')
            if next_period:
                next_period.fully_close_period()

    
    def partially_close_next_period(self):
        period_obj = self.env['account.period']
        for company in self:
            next_period = period_obj.search([
                ('date_end', '>', company.period_lock_date),
                ('state', '!=', 'partially_closed'),
                ('company_id', '=', company.id),
            ], limit=1, order='date_end')
            if next_period:
                next_period.partially_close_period()

    
    def fully_reopen_previous_period(self):
        period_obj = self.env['account.period']
        for company in self:
            next_period = period_obj.search([
                ('date_end', '<=', company.fiscalyear_lock_date),
                ('state', '!=', 'open'),
                ('company_id', '=', company.id),
            ], limit=1)
            if next_period:
                next_period.fully_reopen_period()

    
    def partially_reopen_previous_period(self):
        period_obj = self.env['account.period']
        for company in self:
            next_period = period_obj.search([
                ('date_end', '<=', company.period_lock_date),
                ('state', '!=', 'partially_closed'),
                ('company_id', '=', company.id),
            ], limit=1)
            if next_period:
                next_period.partially_reopen_period()

    
    def write(self, values):
        """
        Track the lock dates
        """
        tracks = []
        if 'period_lock_date' in values:
            tracks.append(_('Period lock date changed to \'%s\'.') % values['period_lock_date'])
        if 'fiscalyear_lock_date' in values:
            tracks.append(_('Fiscal year lock date changed to \'%s\'.') % values['fiscalyear_lock_date'])
        if tracks:
            self.message_post(body='<br/>'.join(tracks))

        return super(ResCompany, self).write(values)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
