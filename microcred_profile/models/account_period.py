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


class AccountPeriod(models.Model):
    _name = 'account.period'
    _description = 'Account period'
    _order = 'date_end desc'

    name = fields.Char(string='Name', size=10, help='The period\'s name', readonly=True, )
    date_start = fields.Date(string='Start date', help='Enter the start date.', required=True, index=True, )
    date_end = fields.Date(string='End date', help='Enter the end date.', required=True, index=True, )
    state = fields.Selection([
        ('open', 'Open'),
        ('partially_closed', 'Partially closed'),
        ('fully_closed', 'Fully closed'),
    ], string='State', help='The period\'s status.', readonly=True, required=True, default='open')
    company_id = fields.Many2one('res.company', string='Periods', help='Periods', readonly=True, )

    
    def partially_close_period(self):
        max_date = False
        for date in self.mapped('date_end'):
            if not max_date or max_date < date:
                max_date = date
        periods_to_close = self.search([
            ('date_end', '<=', max_date),
            ('state', '=', 'open')])
        periods_to_close.write({'state': 'partially_closed'})
        if max_date:
            vals = {
                'period_lock_date': max_date,
                'period_ids': [(5, 0), (6, 0, self.env.user.company_id.period_ids.ids)],
            }
            self.sudo().env.user.company_id.write(vals)

    
    def fully_close_period(self):
        max_date = False
        for date in self.mapped('date_end'):
            if not max_date or max_date < date:
                max_date = date
        periods_to_close = self.search([
            ('date_end', '<=', max_date),
            ('state', '!=', 'fully_closed')])
        periods_to_close.write({'state': 'fully_closed'})
        if max_date:
            vals = {
                'fiscalyear_lock_date': max_date,
                'period_ids': [(5, 0), (6, 0, self.env.user.company_id.period_ids.ids)],
            }
            if self.sudo().env.user.company_id.period_lock_date < max_date:
                vals['period_lock_date'] = max_date
            self.sudo().env.user.company_id.write(vals)

    
    def partially_reopen_period(self):
        min_date = False
        for date in self.mapped('date_start'):
            if not min_date or min_date > date:
                min_date = date
        periods_to_close = self.search([
            ('date_start', '>=', min_date),
            ('state', '=', 'fully_closed')])
        periods_to_close.write({'state': 'partially_closed'})
        if min_date:
            vals = {
                'fiscalyear_lock_date': (datetime.strptime(min_date, '%Y-%m-%d') + relativedelta(days=-1)).strftime('%Y-%m-%d'),
                'period_ids': [(5, 0), (6, 0, self.env.user.company_id.period_ids.ids)],
            }
            self.sudo().env.user.company_id.write(vals)

    
    def fully_reopen_period(self):
        min_date = False
        for date in self.mapped('date_start'):
            if not min_date or min_date > date:
                min_date = date
        periods_to_close = self.search([
            ('date_start', '>=', min_date),
            ('state', '!=', 'open')])
        periods_to_close.write({'state': 'open'})
        if min_date:
            vals = {
                'period_lock_date': (datetime.strptime(min_date, '%Y-%m-%d') + relativedelta(days=-1)).strftime('%Y-%m-%d'),
                'period_ids': [(5, 0), (6, 0, self.env.user.company_id.period_ids.ids)],
            }
            if self.sudo().env.user.company_id.fiscalyear_lock_date > min_date:
                vals['fiscalyear_lock_date'] = vals['period_lock_date']
            self.sudo().env.user.company_id.write(vals)

    @api.onchange('date_end')
    def set_name(self):
        for period in self:
            if period.date_end:
                period.name = datetime.strptime(period.date_end, '%Y-%m-%d').strftime('%m-%Y')
            else:
                period.name = "??????"

    @api.model
    def create(self, values):
        """
        Set the name (as it's a readonly field)
        """
        values['name'] = datetime.strptime(values['date_end'], '%Y-%m-%d').strftime('%m-%Y')
        ret = super(AccountPeriod, self).create(values)
        # TODO: Test for overlaps
        return ret

    
    def write(self, values):
        """
        Set the name (as it's a readonly field)
        """
        if values.get('date_end'):
            values['name'] = datetime.strptime(values['date_end'], '%Y-%m-%d').strftime('%m-%Y')
        ret = super(AccountPeriod, self).write(values)
        # TODO: Test for overlaps
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
