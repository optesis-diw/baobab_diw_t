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

from datetime import datetime
from odoo import models, api, fields
import base64
from odoo.tools.translate import _
from odoo.tools import float_round, float_is_zero
from collections import defaultdict
from io import StringIO
from odoo.tools.misc import xlwt


class WizardExportJournalItem(models.TransientModel):
    _name = "wizard.export.journal.items"
    _description = "Journal item export wizard"

    date_range = fields.Selection(selection=[
        ('no_date', 'No date'),
        ('date2date', 'Date to date'),
        ('period2period', 'Period to period'),
    ], string='Date range', help='Select the date range required.', default='period2period')
    date_from = fields.Date(string='date From', help='Select the date from which the export should take data into account.')
    date_to = fields.Date(string='journal date From', help='Select the date from which the export should take data into account.')
    period_from_id = fields.Many2one(comodel_name='account.period', string='item date From', help='Select the period from which the move lines should be taken into account.')
    period_to_id = fields.Many2one(comodel_name='account.period', string='to', help='Select the period from which the move lines should be taken into account.')
    journal_ids = fields.Many2many(comodel_name='account.journal', string='Journals', help='Select the journal(s) to export. If none are in the list, then all journals will be exported.')
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    today = fields.Date(string='Today')

    name = fields.Char(string='Name', size=64, help='Filename', default="budgets.xls")
    data = fields.Binary(string='Data', help='The file')
    state = fields.Selection([('data', 'Data'), ('export', 'Export')], string='State', default='data')

    
    def get_journals(self):
        model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            active_id = self.env.context.get('active_id')
            if active_id:
                active_ids = [active_id]

        if active_ids:
            journals = self.env['account.journal']
            if model == 'account.move.line':
                journals = self.env['account.journal'].search([('company_id', '=', self.company_id.id or self.env.user.company_id.id)])
            elif model == 'account.journal':
                journals = self.env[model].browse(active_ids)

            return (True, journals)

        return (False, False)

    @api.model
    def default_get(self, fields_list):
        """
        Get the max and min dates
        """

        values = super(WizardExportJournalItem, self).default_get(fields_list)

        values['today'] = datetime.now().strftime('%Y-%m-%d')
        values['company_id'] = self.env.user.company_id.id

        (found, journals) = self.get_journals()
        if found:
            values['journal_ids'] = [(6, 0, journals.ids)]

        return values

    @api.onchange('company_id')
    def onchange_company(self):
        # Delete all journals
        (found, journals) = self.get_journals()

        if found:
            self.update({
                'journal_ids': [(6, 0, journals.ids)],
            })

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

    
    def _get_name(self):
        for export in self:
            export.name = _('%s [%s]') % (export.date_export, export.journal_id.code or export.journal_id.name)

    
    def validate(self):

        def create_tag_name(tags):
            name = ''
            for tag in tags:
                name += tag
            return name

        def excel_addrow(worksheet, linenum, row, form, styles, style=False):
            for col in range(len(row)):
                if style:
                    worksheet.write(linenum - 1, col, row[col], style)
                elif form and styles.get(form[col]):
                    worksheet.write(linenum - 1, col, row[col], styles[form[col]])
                else:
                    worksheet.write(linenum - 1, col, row[col])

        self.ensure_one()

        header1 = [
            'Code journal',
            'Date',
            'N piece',
            'N compte general',
            'Libelle Sage',
            'Montant',
        ]
        header2 = [
            '',
            '',
            '',
            '',
            '',
            '',
        ]
        axes = self.env['account.axis'].search([('sage_export', '=', True), ('company_id', '=', self.company_id.id)], order='number')
        axis_3_name = 'Axis 3'
        axis_4_name = 'Axis 4'
        for axis in axes:
            if axis.number == 3:
                axis_3_name = axis.name
            if axis.number == 4:
                axis_4_name = axis.name

        domain = [
            ('account_id.authorise_analytics', '=', True),
        ]
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        lines = self.env['account.move.line'].search(domain)
        data_lines = []

        if not lines:
            return False

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Budget export')
        header_bold = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour pink;")
        self.name = 'budgets.xls'
        styles = {
            'T': False,  # Text
            'F': xlwt.easyxf("", num_format_str='# ##0.00'),  # Float
        }

        axes_used = {}

        for line in lines:
            line_dico = {
                'Code journal': line.journal_id.code,
                'Date': datetime.strftime(fields.Date.to_datime(line.date), '%Y%m%d'),
                'N piece': line.move_id.name,
                'N compte general': line.account_id.code,
                'Libelle Sage': line.name,
            }
            for tag in line.all_tag_ids:
                if tag.axis_id.number not in (3, 4):  # These are handled differently
                    if tag.axis_id.axis_type == 'multi':
                        key = '#{axis_number}-{tag_name}'.format(axis_number=tag.axis_id.number, tag_name=tag.name)
                        line_dico[key] = tag.name
                        axes_used[key] = True
                    else:
                        line_dico[tag.axis_id.name] = tag.name

            percents = defaultdict(float)
            amounts = defaultdict(float)
            if line.distribution_partner_ids:
                for distribution in line.distribution_partner_ids:
                    tag4 = distribution.budget_partner_id.get_tags(4)
                    if tag4:
                        percents[(False, tag4)] += float_round(distribution.amount_fixed / (line.debit or line.credit or 0.001), precision_digits=6)
                    else:
                        percents[(False, False)] += float_round(distribution.amount_fixed / (line.debit or line.credit or 0.001), precision_digits=6)
            else:
                percents[(False, False)] = 1.0

            if line.budget_element_id.distribution_budget_ids:
                new_percents = defaultdict(float)
                percent_remaining = 100
                for distribution in line.budget_element_id.distribution_budget_ids:
                    element = distribution.child_id
                    tag3 = element.get_tags(3)
                    while not tag3 and element:
                        element = element.budget_id
                        tag3 = element and element.get_tags(3)
                    if not tag3:
                        element = distribution.child_id
                        tag3 = element.budget_department_id.get_tags(3)
                        while not tag3 and element:
                            element = element.budget_id
                            tag3 = element and element.budget_department_id.get_tags(3)
                    for percent in percents:
                        new_percents[(tag3, percent[1])] += float_round((percents[percent] * distribution.equivalent_percentage) / 100.0, precision_digits=6)
                    percent_remaining -= float_round(distribution.equivalent_percentage, precision_digits=6)
                if percent_remaining > 0.0:
                    for percent in percents:
                        new_percents[(False, percent[1])] += float_round((percents[percent] * percent_remaining) / 100.0, precision_digits=6)

                percents = new_percents.copy()

            new_percents = defaultdict(float)
            for key in percents:
                remaining = 1.0
                (tag3, tag4) = key
                # Use the line's values if none were found (because of non-distributions)
                if not tag3:
                    tag3 = line.all_tag_ids.filtered(lambda r: r.axis_id.number == 3)
                tag3text = ''
                if tag3:
                    tag3text = tag3.name

                if not tag4:
                    tag4 = line.all_tag_ids.filtered(lambda r: r.axis_id.number == 4)
                tag4text = ''
                if tag4:
                    tag4 = self.env['account.axis.tag'].search([('id', 'in', tag4.ids)], order='subgroup')
                    tag4text = ''.join(tag4.mapped('name'))

                new_key = (tag3text, tag4text)
                new_percents[new_key] = float_round(percents[key], precision_digits=6)

            total = 0.0
            top_key = False
            top_amount = 0.0
            for key in new_percents:
                amount = float_round(new_percents[key] * (line.credit or line.debit), precision_digits=2)
                total += amount
                amounts[key] = amount
                if amount > top_amount:
                    top_amount = amount
                    top_key = key
            remaining = float_round((line.credit or line.debit) - total, precision_digits=6)
            if not float_is_zero(remaining, precision_digits=2):
                amounts[top_key] = float_round(amounts[top_key] + remaining, precision_digits=2)

            for key in sorted(amounts):
                line_dico.update({
                    axis_3_name: key and key[0] or '',
                    axis_4_name: key and key[1] or '',
                    'Montant': float_round(amounts[key], precision_digits=2)
                })
                data_lines.append(line_dico.copy())

        columns = header1
        form = 'TTTTTF'
        keys_found = {}
        for axis in axes:
            if axis.axis_type == 'multi':
                for tag in axis.value_ids:
                    key = '#{axis_number}-{tag_name}'.format(axis_number=axis.number, tag_name=tag.name)
                    if key in axes_used and key not in keys_found:
                        columns.append(key)
                        header1.append(axis.name)
                        header2.append(tag.name)
                        keys_found[key] = True
                        form += 'T'
            else:
                header1.append(axis.name)
                header2.append('')
                form += 'T'

        excel_addrow(worksheet, 1, header1, '', styles, style=header_bold)
        excel_addrow(worksheet, 2, header2, '', styles, style=header_bold)

        row_number = 3
        for line in data_lines:
            data_line = []
            for column in columns:
                data_line.append(line.get(column, ''))

            excel_addrow(worksheet, row_number, data_line, form, styles)
            row_number += 1

        stream = StringIO()
        workbook.save(stream)
        this_file = stream.getvalue()
        vals = {
            'data': base64.encodestring(this_file),
            'state': 'export',
        }
        self.write(vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.export.journal.items',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
