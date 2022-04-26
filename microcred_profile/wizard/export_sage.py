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
from datetime import datetime


class WizardExportSage(models.TransientModel):
    _name = "wizard.export.sage"
    _description = "Export SAGE wizard"

    date_range = fields.Selection(selection=[
        ('no_date', 'No date'),
        ('date2date', 'Date to date'),
        ('period2period', 'Period to period'),
    ], string='Date range', help='Select the date range required.', default='period2period')
    date_from = fields.Date(string='export date From', help='Select the date from which the export should take data into account.')
    date_to = fields.Date(string='date to', help='Select the date from which the export should take data into account.')
    period_from_id = fields.Many2one(comodel_name='account.period', string='periode date From', help='Select the period from which the move lines should be taken into account.')
    period_to_id = fields.Many2one(comodel_name='account.period', string='to', help='Select the period from which the move lines should be taken into account.')
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', help='The journal selected.', readonly=True, )
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    today = fields.Date(string='Today')

    @api.model
    def default_get(self, fields_list):
        """
        Get the max and min dates
        """

        values = super(WizardExportSage, self).default_get(fields_list)

        values['today'] = datetime.now().strftime('%Y-%m-%d')
        if self.env.context.get('active_id'):
            values['journal_id'] = self.env.context.get('active_id')
            values['company_id'] = self.env['account.journal'].browse(self.env.context['active_id']).company_id.id

        return values

    @api.onchange('period_from_id')
    def onchange_period_from(self):
        if self.period_from_id:
            end_periods = self.period_from_id.search([
                ('date_start', '>=', self.period_from_id.date_start),
                ('date_start', '<=', self.today),
                ('company_id', '=', self.company_id.id),
            ])
            if not self.period_to_id or self.period_to_id not in end_periods:
                self.period_to_id = self.period_from_id.id
            return {
                'domain': {
                    'period_to_id': [('id', 'in', end_periods.ids)],
                }
            }

    
    def validate(self):
        export_ids = []
        for wizard in self:
            date_from = False
            date_to = False
            if wizard.date_range == 'date2date':
                date_from = min(wizard.date_from, wizard.date_to)
                date_to = max(wizard.date_from, wizard.date_to)
            elif wizard.date_range == 'period2period':
                date_from = wizard.period_from_id.date_start
                date_to = wizard.period_to_id.date_end

            self.ensure_one()
            vals = {
                'journal_id': wizard.journal_id.id,
                'date_from': date_from,
                'date_to': date_to,
            }
            export = self.env['account.journal.sage.export'].create(vals)
            if export.generate_file():
                export_ids.append(export.id)
            else:
                export.unlink()

        if export_ids:
            action = self.env.ref('microcred_profile.action_account_journal_sage_export', False)
            action_data = action.read()[0]

            action_data.update(
                domain=[('id', 'in', export_ids)],
                context={
                    'target': 'new',
                }
            )
            return action_data

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
