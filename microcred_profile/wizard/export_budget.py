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
from collections import defaultdict
from io import StringIO
import csv
import base64
from odoo.tools.translate import _
from odoo.tools.misc import xlwt


class WizardExportBudget(models.TransientModel):
    _name = "wizard.export.budget"
    _description = "Export budget"

    date_range = fields.Selection([
        ('range', 'Range'),
        ('M', 'This month'),
        ('M-1', 'Last month'),
        ('Y', 'This year'),
        ('Y-1', 'Last year'),
        ('Y12M', '12 months sliding'),
    ], string='Date range', help='Select the range of dates that will be exported.', required=True, default='range')
    date_start = fields.Date(string='Start date', help='Enter the start date.')
    date_end = fields.Date(string='End date', help='Enter the end date.')
    budget_ids = fields.Many2many('budget.element', string='Budgets to export', help='Select the budgets to export.', required=True, )
    #main_budget_ids = fields.Many2many('budget.element', string='Budgets to export', help='Select the budgets to export.', required=True, )
    presentation = fields.Selection([
        ('columns', 'Months in Columns'),
        ('rows', 'Months in Rows'),
    ], string='Presentation', help='Select how months should be represented.', required=True, default='columns')
    include_generated = fields.Boolean(string='Include automatically generated lines', help='Check this box if you want to export the automatically generated lines.', default=False)
    state = fields.Selection([('data', 'Data'), ('export', 'Export')], string='State', default='data')
    name = fields.Char(string='Name', size=64, help='Filename', default="budgets.csv")
    data = fields.Binary(string='Data', help='The file')
    company_ids = fields.Many2many(comodel_name='res.company', string='Companies', help='Select the company(s) to export.', required=True)
    view_type = fields.Selection(selection=[
        ('per_budget', 'Per budget'),
        ('consolidated', 'Consolidated'),
    ], string='View type', default='consolidated', required=True,
        help='Select the type of view:\n\'Per budget\': The lines are regrouped by budget and in their local currency.\n\'Consolidated\': The lines are grouped by department and by line type, in the holding\'s currency.')

    @api.model
    def default_get(self, fields_list):
        """
        Get the max and min dates
        """

        values = super(WizardExportBudget, self).default_get(fields_list)

        budget_list = self.env.context.get('active_ids')
        if not budget_list and self.env.context.get('active_id'):
            budget_list = [self.env.context.get('active_id')]

        if budget_list:
            elements = self.env['budget.element'].browse(budget_list)
            budget_ids = []
            for element in elements:
                if element.type in ('periodic', 'project'):
                    if element.id not in budget_ids:
                        budget_ids.append(element.id)
                elif element.type == 'budget_line':
                    if element.budget_id not in budget_ids:
                        budget_ids.append(element.budget_id.id)
                elif element.type == 'budget_detail':
                    if element.budget_id.budget_id not in budget_ids:
                        budget_ids.append(element.budget_id.budget_id.id)

            budgets = elements.browse(budget_ids)
            values['budget_ids'] = [(6, 0, [x.id for x in budgets])]
            extra_budgets = budgets.mapped('affected_budget_ids.parent_id')  # get sub-budgets
            while extra_budgets:
                budgets += extra_budgets
                extra_budgets = extra_budgets.mapped('affected_budget_ids.parent_id')  # get sub-budgets of sub-budgets

            values['budget_ids'] = [(6, 0, [x.id for x in budgets])]
            date_start = False
            date_end = False
            for budget in budgets:
                if not date_start or date_start > budget.date_start:
                    date_start = budget.date_start
                if not date_end or date_end < budget.date_end:
                    date_end = budget.date_end
            values['company_ids'] = [(6, 0, [x.id for x in budgets.mapped('company_id')])]
            values['date_start'] = date_start
            values['date_end'] = date_end

        return values

    
    def get_budgets(self):
        """
        Get the budgets associated with the criteria selected
        """
        self.ensure_one()
        return self.budget_ids.filtered(lambda r: r.company_id in self.company_ids)

    
    def generate_file(self, file_type):
        def format_number(number, file_type):
            if file_type == 'csv':
                return '%.2f' % number

            return number

        def month_start(date):
            return date + relativedelta(day=1)

        def month_end(date):
            return date + relativedelta(months=1, day=1) + relativedelta(days=-1)

        def get_axes(element, axis_list):
            axis_tags = defaultdict(str)
            for axis_number in axis_list:
                tags = element.get_tags(axis_number)
                axis_tags[axis_number] = ''
                if tags:
                    axis = tags[0].axis_id
                    tags = self.env['account.axis.tag'].search([('id', 'in', tags.ids)], order='subgroup')
                    name = ''
                    if axis.axis_type == 'multi':
                        name = ' '.join([x.name for x in tags])
                    else:
                        for tag in tags:
                            name += tag.name
                    axis_tags[axis_number] = name

            all_tags = []
            for tag in sorted(axis_tags.keys()):
                all_tags.append(axis_tags[tag])

            return all_tags

        def add_amounts(amounts, amount1, amount2, amount3):
            return(amounts[0] + amount1, amounts[1] + amount2, amounts[2] + amount3)

        def get_budget_consolidated_data(line_num, line_name_1, line_name_2, line_name_3, period, axis_list, file_type, element_amounts):
            axis_tags = ['' for number in axis_list]

            ret = [
                line_num
            ]
            form = 'N'
            ret.extend(axis_tags)
            form += 'T' * len(axis_tags)

            ret.extend([
                '',
                line_name_1,
                line_name_2,
                line_name_3,
                '',
                '',
                period,
                format_number(element_amounts[0], file_type),
                format_number(element_amounts[1], file_type),
                format_number(element_amounts[2], file_type),
            ])
            form += 'ETTTTTNEFG'
            return (ret, form)

        def get_budget_data(line_num, element, period, axis_list, file_type, element_amounts):
            budget = element
            budget_detail = ''
            budget_line = ''
            if element.type == 'budget_line':
                budget = element.budget_id
                budget_line = element.name
            elif element.type == 'budget_detail':
                budget = element.budget_id.budget_id
                budget_line = element.budget_id.name
                budget_detail = element.name

            axis_tags = get_axes(element, axis_list)

            ret = [
                line_num
            ]
            form = 'N'
            ret.extend(axis_tags)
            form += 'T' * len(axis_tags)

            ret.extend([
                budget.name,
                budget.budget_department_id.name or '',
                budget.code or '',
                budget.type,
                budget_line or '',
                budget_detail or '',
                period,
                format_number(element_amounts[0], file_type),
                format_number(element_amounts[1], file_type),
                format_number(element_amounts[2], file_type),
            ])
            form += 'ETTTTTNEFG'
            return (ret, form)

        def excel_addrow(worksheet, linenum, row, form, styles, line_type=False, style=False):
            for col in range(len(row)):
                if style:
                    worksheet.write(linenum - 1, col, row[col], style)
                elif form and styles.get(form[col] + line_type):
                    worksheet.write(linenum - 1, col, row[col], styles[form[col] + line_type])
                else:
                    worksheet.write(linenum - 1, col, row[col])

        def csv_addrow(csv_writer, row):
            new_row = []
            for col in range(len(row)):
                new_row = unicode(row[col]).encode('utf-8')
            csv_writer.writerow(new_row)

        def convert_currency(amount, currency, currency_table):
            return amount * currency_table[currency]

        self.ensure_one()
        budget_obj = self.env['budget.element']
        departments = self.env['budget.element']
        element_period_obj = self.env['budget.element.period']
        date_start = month_start(datetime.strptime(str(self.date_start), '%Y-%m-%d'))
        date_end = month_end(datetime.strptime(str(self.date_end), '%Y-%m-%d'))
        all_axes = self.env['account.axis'].search([], order='number asc').mapped('number')
        axis_list = []
        for number in all_axes:
            if number not in axis_list:
                axis_list.append(number)
        is_consolidated = (self.view_type == 'consolidated')
        holding = self.env['res.company'].sudo().search([('parent_id', '=', False)], limit=1, order='id')

        # Firstly, recalculate all periods of required budgets and budget lines, from bottom-to-top
        all_budgets = self.get_budgets()
        if self.include_generated:
            extra_budgets = all_budgets.mapped('affected_budget_ids.parent_id')  # get sub-budgets
            while extra_budgets:
                all_budgets += extra_budgets
                extra_budgets = extra_budgets.mapped('affected_budget_ids.parent_id')  # get sub-budgets of sub-budgets

        (max_depth, depths) = all_budgets.calculate_depths()
        while max_depth > 0:
            level_ids = []
            for element_id in depths.keys():
                if depths[element_id] == max_depth:
                    level_ids.append(element_id)
            if level_ids:
                element_period_obj.search([
                    ('budget_element_id', 'in', level_ids)
                ]).set_invoiced_amount()
            max_depth -= 1

        if self.date_range == 'M':
            date_start = month_start(datetime.now())
            date_end = month_end(datetime.now())
        elif self.date_range == 'M-1':
            date_start = month_start(datetime.now() + relativedelta(months=-1))
            date_end = month_end(datetime.now() + relativedelta(months=-1))
        elif self.date_range == 'Y':
            date_start = month_start(datetime.now() + relativedelta(month=1, day=1))
            date_end = month_end(datetime.now() + relativedelta(month=12, day=1))
        elif self.date_range == 'Y-1':
            date_start = month_start(datetime.now() + relativedelta(years=-1, month=1, day=1))
            date_end = month_end(datetime.now() + relativedelta(years=-1, month=12, day=1))
        elif self.date_range == 'Y12M':
            date_start = month_start(datetime.now() + relativedelta(years=-1, days=1))
            date_end = month_end(datetime.now())

        # Get the list of periods (it's always monthly)
        period_list = []
        cur_date = date_start
        while cur_date < date_end:
            period_list.append(cur_date.strftime('%Y-%m'))
            cur_date = cur_date + relativedelta(months=1)

        # Get the equivalents for the companies
        company_periods = {}
        found_periods = [0]
        for company in self.company_ids:
            for period in period_list:
                period_items = self.env['account.period'].search([
                    ('date_start', '<=', period + "-01"),
                    ('date_end', '>=', period + "-01"),
                    ('company_id', '=', company.id),
                    ('id', 'not in' ,[found_periods])
                ])
                company_periods[(company, period)] = period_items.ids
                if period_items:
                    found_periods.append(period_items.ids)

        currency_table = {}
        budget_element_ids = []
        budget_consolidate = defaultdict(list)
        for budget in self.get_budgets():
            if budget.budget_department_id:
                departments |= budget.budget_department_id

            budget_element_ids.append(budget.id)
            currency_table[budget.currency_id] = 1.0
            if budget.type in ('periodic', 'project'):
                for budget_line in budget.budget_line_ids:
                    budget_element_ids.append(budget_line.id)

                    if not budget_line.budget_detail_ids:  # No details so we add the line (otherwise, it's just the details that are added)
                        budget_consolidate[(budget_line.budget_department_id or budget.budget_department_id, budget_line.budget_line_type_id)].append(budget_line.id)

                    for budget_detail in budget_line.budget_detail_ids:
                        budget_element_ids.append(budget_detail.id)
                        budget_consolidate[(budget_detail.budget_department_id or budget_line.budget_department_id or budget.budget_department_id, budget_detail.budget_line_type_id)].append(budget_detail.id)

            elif budget.type == 'budget_line':
                budget_element_ids.append(budget.id)
                if not budget.budget_detail_ids:  # No details so we add the line (otherwise, it's just the details that are added)
                    budget_consolidate[(budget_line.budget_department_id, budget.budget_line_type_id)].append(budget.id)

                for budget_detail in budget.budget_detail_ids:
                    budget_element_ids.append(budget_detail.id)
                    budget_consolidate[(budget_detail.budget_department_id or budget_line.budget_department_id, budget_detail.budget_line_type_id)].append(budget_detail.id)

            else:  # Detail or others
                budget_element_ids.append(budget.id)
                if budget.type == 'budget_detail':
                    budget_consolidate[(budget.budget_department_id, budget.budget_line_type_id)].append(budget_line.id)

        if is_consolidated:
            # Recreate the list so that it is in consolidated format
            no_line_type = self.env['budget.line.type']
            line_types = self.env['budget.line.type'].search([('parent_id', '=', False)], order='sequence, name')
            budget_element_ids = []
            for department in departments.sorted(lambda r: r.name):
                for line_type in line_types.sorted(key=lambda r: r.full_sequence):
                    if budget_consolidate[(department, line_type)]:
                        budget_element_ids.extend(budget_consolidate[(department, line_type)])
                    if line_type.child_ids:
                        for child_line_type in line_type.child_ids.sorted(key=lambda r: r.full_sequence):
                            if budget_consolidate[(department, child_line_type)]:
                                budget_element_ids.extend(budget_consolidate[(department, child_line_type)])
                if budget_consolidate[(department, no_line_type)]:
                    budget_element_ids.extend(budget_consolidate[(department, no_line_type)])

            # Get currency conversions
            for currency in currency_table:
                if currency != holding.currency_id:
                    currency_table[currency] = currency.sudo().compute(1, holding.sudo().currency_id, round=False)

        stream = StringIO()
        if file_type == 'csv':
            csv_writer = csv.writer(stream, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        elif file_type == 'excel':
            workbook = xlwt.Workbook()
            worksheet = workbook.add_sheet('Budget export')
            bottom_line = xlwt.easyxf("borders: top medium;")
            self.name = 'budgets.xls'
            styles = {
                'TH': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour pink; align: horiz center; borders: top medium, bottom medium;"),
                'EH': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour pink; align: horiz center; borders: left medium, top medium, bottom medium;", num_format_str='# ### ### ##0.00'),
                'FH': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour pink; align: horiz center; borders: top medium, bottom medium;", num_format_str='# ### ### ##0.00'),
                'GH': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour pink; align: horiz center; borders: right medium, top medium, bottom medium;", num_format_str='# ### ### ##0.00'),
                'NH': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour pink; align: horiz center; borders: right medium, left medium, top medium, bottom medium;"),

                'TZ': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour ocean_blue;"),
                'EZ': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour ocean_blue; borders: left medium;", num_format_str='# ### ### ##0.00'),
                'FZ': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour ocean_blue;", num_format_str='# ### ### ##0.00'),
                'GZ': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour ocean_blue; borders: right medium;", num_format_str='# ### ### ##0.00'),
                'NZ': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour ocean_blue; borders: right medium, left medium;"),

                'TY': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour sky_blue;"),
                'EY': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour sky_blue; borders: left medium;", num_format_str='# ### ### ##0.00'),
                'FY': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour sky_blue;", num_format_str='# ### ### ##0.00'),
                'GY': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour sky_blue; borders: right medium;", num_format_str='# ### ### ##0.00'),
                'NY': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour sky_blue; borders: right medium, left medium;"),

                'TX': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour light_turquoise;"),
                'EX': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour light_turquoise; borders: left medium;", num_format_str='# ### ### ##0.00'),
                'FX': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour light_turquoise;", num_format_str='# ### ### ##0.00'),
                'GX': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour light_turquoise; borders: right medium;", num_format_str='# ### ### ##0.00'),
                'NX': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour light_turquoise; borders: right medium, left medium;"),

                'TB': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray40;"),
                'EB': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray40; borders: left medium;", num_format_str='# ### ### ##0.00'),
                'FB': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray40;", num_format_str='# ### ### ##0.00'),
                'GB': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray40; borders: right medium;", num_format_str='# ### ### ##0.00'),
                'NB': xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray40; borders: right medium, left medium;"),

                'TL': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour gray25;"),
                'EL': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour gray25; borders: left medium;", num_format_str='# ### ### ##0.00'),
                'FL': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour gray25;", num_format_str='# ### ### ##0.00'),
                'GL': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour gray25; borders: right medium;", num_format_str='# ### ### ##0.00'),
                'NL': xlwt.easyxf("font: italic on; pattern: pattern solid, fore_colour gray25; borders: right medium, left medium;"),

                'TD': False,
                'ED': xlwt.easyxf("borders: left medium;", num_format_str='# ##0.00'),
                'FD': xlwt.easyxf("", num_format_str='# ##0.00'),
                'GD': xlwt.easyxf("borders: right medium;", num_format_str='# ##0.00'),
                'ND': xlwt.easyxf("borders: right medium, left medium;"),
            }
            # header_plain = xlwt.easyxf("pattern: pattern solid, fore_colour gray25;")
            # bold = xlwt.easyxf("font: bold on;")

        csv_row = [
            _("Line ID")
        ]
        form = 'T'
        for axis in axis_list:
            csv_row.append(_('Axis {axis}').format(axis=axis))
            form += 'T'

        csv_row.extend([
            _("Budget"),
            _("Budget department"),
            _("Code Budget"),
            _("Budget Type"),
            _("Budget line"),
            _("Budget detail"),
            _("Month"),
            _("Planned"),
            _("Engaged"),
            _("Actual"),
        ])
        form += 'ETTTTTNEFG'
        if self.presentation == 'columns':
            for period in period_list:
                csv_row.append(_('%s - PLAN') % period)
                csv_row.append(_('%s - ACT') % period)
                form += 'EG'
        else:
            csv_row.append(_('PLAN'))
            csv_row.append(_('ACT'))
            form += 'EG'

        if file_type == 'csv':
            csv_addrow(csv_writer, csv_row)
        elif file_type == 'excel':
            excel_addrow(worksheet, 1, csv_row, form, styles, line_type='H')
            # excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type=element.budget_line_type_id.parent_id and 'X' or 'Y')

        company_coeffs = {}
        for company in self.env['res.company'].sudo().search([]):
            company_coeffs[company] = (100.0 + company.sudo().default_transfer_charge) / 100.0

        line_num = 1
        element_amounts = {}
        if is_consolidated:
            element_browse = budget_obj.browse(budget_element_ids).filtered(lambda r: r.company_id in self.company_ids)
        else:
            element_browse = budget_obj.browse(budget_element_ids).filtered(lambda r: r.company_id in self.company_ids).sorted(lambda r: r.name)

        for element in element_browse:
            total_amount_fixed = 0.0
            total_amount_engaged = 0.0
            total_amount_invoiced = 0.0
            budget_department_id = element.budget_department_id or element.budget_id.budget_department_id or element.budget_id.budget_id.budget_department_id
            for period in period_list:
                element_periods = element_period_obj.search([
                    ('budget_element_id', '=', element.id),
                    ('period_id', 'in', company_periods[(element.company_id, period)]),
                ])
                amount_fixed = 0.0
                amount_engaged = 0.0
                amount_invoiced = 0.0
                for element_period in element_periods:
                    amount_fixed += convert_currency(element_period.profit_loss_amount_fixed, element.currency_id, currency_table) * company_coeffs[element.company_id]
                    amount_engaged += convert_currency(element_period.profit_loss_amount_engaged, element.currency_id, currency_table) * company_coeffs[element.company_id]
                    amount_invoiced += convert_currency(element_period.profit_loss_amount_invoiced, element.currency_id, currency_table) * company_coeffs[element.company_id]

                total_amount_fixed += amount_fixed
                total_amount_engaged += amount_engaged
                total_amount_invoiced += amount_invoiced
                element_amounts[(period, element, False, False)] = add_amounts(element_amounts.get((period, element, False, False), (0.0, 0.0, 0.0)), amount_fixed, amount_engaged, amount_invoiced)
                if is_consolidated:
                    element_amounts[(period, False, budget_department_id, False)] = add_amounts(element_amounts.get((period, False, budget_department_id, False), (0.0, 0.0, 0.0)), amount_fixed, amount_engaged, amount_invoiced)
                    element_amounts[(period, False, budget_department_id, element.budget_line_type_id)] = add_amounts(element_amounts.get((period, False, budget_department_id, element.budget_line_type_id), (0.0, 0.0, 0.0)), amount_fixed, amount_engaged, amount_invoiced)
                    if element.budget_line_type_id.parent_id:
                        element_amounts[(period, False, budget_department_id, element.budget_line_type_id.parent_id)] = add_amounts(element_amounts.get((period, False, budget_department_id, element.budget_line_type_id.parent_id), (0.0, 0.0, 0.0)), amount_fixed, amount_engaged, amount_invoiced)

            element_amounts[(False, element, False, False)] = (total_amount_fixed, total_amount_engaged, total_amount_invoiced)
            if is_consolidated:
                element_amounts[(False, False, budget_department_id, False)] = add_amounts(element_amounts.get((False, False, budget_department_id, False), (0.0, 0.0, 0.0)), total_amount_fixed, total_amount_engaged, total_amount_invoiced)
                element_amounts[(False, False, budget_department_id, element.budget_line_type_id)] = add_amounts(element_amounts.get((False, False, budget_department_id, element.budget_line_type_id), (0.0, 0.0, 0.0)), total_amount_fixed, total_amount_engaged, total_amount_invoiced)
                if element.budget_line_type_id.parent_id:
                    element_amounts[(False, False, budget_department_id, element.budget_line_type_id.parent_id)] = add_amounts(element_amounts.get((False, False, budget_department_id, element.budget_line_type_id.parent_id), (0.0, 0.0, 0.0)), total_amount_fixed, total_amount_engaged, total_amount_invoiced)

        last_key = (False, False)
        last_parent = False
        if self.presentation == 'rows':
            # Do the months/periods by rows
            for period in period_list:
                for element in element_browse:
                    budget_department_id = element.budget_department_id or element.budget_id.budget_department_id or element.budget_id.budget_id.budget_department_id
                    if is_consolidated:
                        if last_key != (budget_department_id, element.budget_line_type_id):
                            if budget_department_id != last_key[0]:
                                (csv_row, csv_format) = get_budget_consolidated_data(line_num, budget_department_id.name, '', '', period, axis_list, file_type, element_amounts[(False, False, budget_department_id, False)])
                                period_amount = element_amounts.get((period, False, budget_department_id, False), (0.0, 0.0, 0.0))
                                csv_row.append(format_number(period_amount[0], file_type))
                                csv_row.append(format_number(period_amount[2], file_type))
                                csv_format += 'EG'
                                line_num += 1
                                if file_type == 'csv':
                                    csv_addrow(csv_writer, csv_row)
                                elif file_type == 'excel':
                                    excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type='Z')

                            if last_key[1] and last_key[1].parent_id != element.budget_line_type_id.parent_id:
                                pass

                            (csv_row, csv_format) = get_budget_consolidated_data(line_num, '', element.budget_line_type_id.name or _('<None>'), '', period, axis_list, file_type, element_amounts[(False, False, budget_department_id, element.budget_line_type_id)])
                            period_amount = element_amounts.get((period, False, budget_department_id, element.budget_line_type_id), (0.0, 0.0, 0.0))
                            csv_row.append(format_number(period_amount[0], file_type))
                            csv_row.append(format_number(period_amount[2], file_type))
                            csv_format += 'EG'
                            line_num += 1
                            if file_type == 'csv':
                                csv_addrow(csv_writer, csv_row)
                            elif file_type == 'excel':
                                excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type='X')

                            last_key = (budget_department_id, element.budget_line_type_id)

                    (csv_row, csv_format) = get_budget_data(line_num, element, period, axis_list, file_type, element_amounts[(False, element, False, False)])
                    period_amount = element_amounts.get((period, element, False, False), (0.0, 0.0, 0.0))
                    csv_row.append(format_number(period_amount[0], file_type))
                    csv_row.append(format_number(period_amount[2], file_type))
                    csv_format += 'EG'
                    line_num += 1
                    if file_type == 'csv':
                        csv_addrow(csv_writer, csv_row)
                    elif file_type == 'excel':
                        line_type = 'D'
                        if element.type == 'periodic':
                            line_type = 'B'
                        elif element.type == 'budget_line':
                            line_type = 'L'
                        excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type=line_type)
        else:
            for element in element_browse:
                budget_department_id = element.budget_department_id or element.budget_id.budget_department_id or element.budget_id.budget_id.budget_department_id
                if is_consolidated:
                    if last_key != (budget_department_id, element.budget_line_type_id):
                        if budget_department_id != last_key[0]:
                            last_parent = False
                            last_key = (False, False)
                            (csv_row, csv_format) = get_budget_consolidated_data(line_num, budget_department_id.name, '', '', '', axis_list, file_type, element_amounts[(False, False, budget_department_id, False)])
                            for period in period_list:
                                period_amount = element_amounts.get((period, False, budget_department_id, False), (0.0, 0.0, 0.0))
                                csv_row.append(format_number(period_amount[0], file_type))
                                csv_row.append(format_number(period_amount[2], file_type))
                                csv_format += 'EG'
                            line_num += 1
                            if file_type == 'csv':
                                csv_addrow(csv_writer, csv_row)
                            elif file_type == 'excel':
                                excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type='Z')

                        if last_parent != element.budget_line_type_id.parent_id and element.budget_line_type_id.parent_id:
                            (csv_row, csv_format) = get_budget_consolidated_data(line_num, '', element.budget_line_type_id.parent_id.name or _('<None>'), '', '', axis_list, file_type, element_amounts[(False, False, budget_department_id, element.budget_line_type_id.parent_id)])
                            for period in period_list:
                                period_amount = element_amounts.get((period, False, budget_department_id, element.budget_line_type_id.parent_id), (0.0, 0.0, 0.0))
                                csv_row.append(format_number(period_amount[0], file_type))
                                csv_row.append(format_number(period_amount[2], file_type))
                                csv_format += 'EG'

                            line_num += 1
                            if file_type == 'csv':
                                csv_addrow(csv_writer, csv_row)
                            elif file_type == 'excel':
                                excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type='Y')

                        if element.budget_line_type_id.child_ids:
                            last_parent = element.budget_line_type_id
                        else:
                            last_parent = element.budget_line_type_id.parent_id

                        if element.budget_line_type_id.parent_id:
                            name1 = ''
                            name2 = element.budget_line_type_id.name or _('<None>')
                        else:
                            name1 = element.budget_line_type_id.name or _('<None>')
                            name2 = ''

                        (csv_row, csv_format) = get_budget_consolidated_data(line_num, '', name1, name2, '', axis_list, file_type, element_amounts[(False, False, budget_department_id, element.budget_line_type_id)])
                        for period in period_list:
                            period_amount = element_amounts.get((period, False, budget_department_id, element.budget_line_type_id), (0.0, 0.0, 0.0))
                            csv_row.append(format_number(period_amount[0], file_type))
                            csv_row.append(format_number(period_amount[2], file_type))
                            csv_format += 'EG'

                        line_num += 1
                        if file_type == 'csv':
                            csv_addrow(csv_writer, csv_row)
                        elif file_type == 'excel':
                            excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type=element.budget_line_type_id.parent_id and 'X' or 'Y')

                        last_key = (budget_department_id, element.budget_line_type_id)

                (csv_row, csv_format) = get_budget_data(line_num, element, '', axis_list, file_type, element_amounts[(False, element, False, False)])
                for period in period_list:
                    period_amount = element_amounts.get((period, element, False, False), (0.0, 0.0, 0.0))
                    csv_row.append(format_number(period_amount[0], file_type))
                    csv_row.append(format_number(period_amount[2], file_type))
                    csv_format += 'EG'

                line_num += 1
                if file_type == 'csv':
                    csv_addrow(csv_writer, csv_row)
                elif file_type == 'excel':
                    line_type = 'D'
                    if not is_consolidated:
                        if element.type == 'periodic':
                            line_type = 'B'
                        elif element.type == 'budget_line':
                            line_type = 'L'
                    excel_addrow(worksheet, line_num, csv_row, csv_format, styles, line_type=line_type)

        this_file = False
        if file_type == 'csv':
            this_file = stream.getvalue()
        elif file_type == 'excel':
            for col in range(len(csv_row)):
                worksheet.write(line_num, col, '', bottom_line)
            workbook.save(stream)
            this_file = stream.getvalue()

        self.write({
            'state': 'export',
            'data': base64.encodestring(this_file),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.export.budget',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    
    def validate_excel(self):
        return self.generate_file('excel')

    
    def validate_csv(self):
        return self.generate_file('csv')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
