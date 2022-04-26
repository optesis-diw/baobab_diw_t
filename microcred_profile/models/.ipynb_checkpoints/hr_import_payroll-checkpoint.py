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
import csv
import base64
import re
from odoo.tools.translate import _
from datetime import datetime
from collections import defaultdict


class HrImportPayroll(models.Model):
    _name = 'hr.import.payroll'
    _description = 'Payroll Import'
    _order = 'id desc'

    
    def copy(self, default=None):
        if default is None:
            default = {}

        next_period = self._default_period()
        default.update({
            'period_id': next_period and next_period.id or False,
            'state': 'not_imported',
            'comments': False,
            'move_id': False,
        })

        return super(HrImportPayroll, self).copy(default)

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        journal = self.env['account.journal'].search([
            ('code', '=', 'PAIE'),
            ('company_id', '=', company_id),
        ], limit=1)
        if not journal:
            last_import = self.search([('company_id', '=', company_id)])
            if last_import:
                journal = last_import.journal_id
            else:
                journal = self.env['account.journal'].search([
                    ('type', '=', 'general'),
                    ('company_id', '=', company_id),
                ], limit=1)

        return journal

    @api.model
    def _default_period(self):
        if self._context.get('default_period_id', False):
            return self.env['account.period'].browse(self._context.get('default_period_id'))
        # Get the period after the previous import (logical...)
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        last_imports = self.search([('company_id', '=', company_id)])
        last_import = False
        if last_imports:
            last_date = False
            for this_import in last_imports:
                if not last_date or last_date < this_import.period_id.date_end:
                    last_date = this_import.period_id.date_end
                    last_import = this_import

        period = False
        if last_import:
            period = self.env['account.period'].search([('date_start', '>', last_import.period_id.date_end)], order="date_start asc")
        if not period:
            period = self.env['account.period'].search([('date_end', '<', datetime.today().strftime('%Y-%m-%d'))], order="date_start asc")  # Get the first period that finished
        if period:
            return period[0]
        return False

    name = fields.Char(string='Name', size=64, help='The name of the export.')
    csv_file = fields.Binary(string='CSV File', help='Select the CSV file to import.')
    comments = fields.Text(string='Comments', help='The comments concerning the import', readonly=True, )
    state = fields.Selection([
        ('not_imported', 'Not imported'),
        ('has_errors', 'Has errors'),
        ('imported', 'Imported'),
        ('done', 'Validated'),
    ], string='Import status', default='not_imported', required=True, readonly=True,
        help='The import status:\n* \'Not imported\': The file has yet to be imported.\n* \'Has errors\': The file has not been imported due to errors.\n* \'Imported\': The file has been successfully imported.\n')
    period_id = fields.Many2one('account.period', string='Period', help='The period concerning the import.', required=True, default=_default_period, )
    journal_id = fields.Many2one('account.journal', string='Journal', help='Select the journal', required=True, default=_default_journal,)
    company_id = fields.Many2one('res.company', string='Company', help='Select the company for which the import is made.', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get(object='hr_import_payroll'))
    move_id = fields.Many2one('account.move', string='Account move', help='The account move generated by the import.', readonly=True, )
    separator = fields.Selection(selection=[
        (';', '; (Semi-colon)'),
        (',', ', (Comma)'),
        ('T', '(Tabulation'),
    ], string='Separator', help='Select the separator.', default=";", required=True, )
    encoding = fields.Selection(selection=[
        ('iso-8859-1', 'ISO-8859-1'),
        ('utf-8', 'UTF-8')
    ], string='Encoding', help='The encoding', default="iso-8859-1")

    
    def treat_file(self):
        def correct_cr(matchobj):
            return matchobj.group(0).replace('\n', ' ')

        def get_float(number):
            number = number.replace(',', '.') or '0.0'
            return float(number)

        def convert_to_excel_letters(col):
            """ Convert given row and column number to an Excel-style cell name. """
            LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            result = []
            while col:
                col, rem = divmod(col - 1, 26)
                result[:0] = LETTERS[rem]

            return ''.join(result)

        def get_axes(element, axes):
            axis_tags = {}
            for axis in axes:
                axis_tags[axis] = False

            while element:
                for axis in axes:
                    if not axis_tags[axis]:
                        axis_tags[axis] = element.get_tags(axis.number)
                element = element.budget_id

            tags = self.env['account.axis.tag']
            for axis in axes:
                if axis_tags[axis]:
                    tags |= axis_tags[axis]

            return tags

        employee_obj = self.env['hr.employee']
        element_obj = self.env['budget.element']
        move_lines = []

        for payroll in self:
            bad_employees = []  # Inexisting employees
            multi_employees = []  # Multiple employees

            bad_accounts = []  # Inexisting accounts
            is_no_line_type = {}  # There is no line type for the account
            has_bad_accounts = False
            has_no_line_types = False

            bad_compensations = []  # Accounts without payroll compensation accounts

            bad_departments = {}  # Departments that could not be found
            is_periodics = {}  # Departments found but periodic budgets not found
            has_bad_departments = False
            has_bad_periodics = False

            axes = self.env['account.axis'].search([('company_id', '=', payroll.company_id.id)])

            if payroll.csv_file:
                separator = str(payroll.separator)
                if separator == 'T':
                    separator = '\t'

                errors = ""
                comments = ""
                this_file = base64.decodestring(payroll.csv_file)
                this_file = re.sub("\"[^\"]*\"", correct_cr, this_file)
                this_file = this_file.split('\n')
                reader = csv.reader(this_file, delimiter=separator, quotechar='"')
                line_count = 0
                account_header = []
                accounts = {}
                compensations = {}
                departments = {}
                period = ''
                columns = {}
                employee_data = {}
                employee_keys = []
                new_state = ''
                payroll.move_id.unlink()

                for line in reader:
                    if line:
                        line_count += 1
                        if line_count == 1:
                            account_header = line
                            period = payroll.period_id.name
                            account_header[0] = ''
                            for column_num in range(len(line)):  # Get the account data
                                if account_header[column_num]:
                                    account_code = account_header[column_num]
                                    account = self.env['account.account'].search([
                                        ('code', '=', account_header[column_num]),
                                        ('company_id', '=', payroll.company_id.id),
                                    ])
                                    if account:
                                        accounts[account_code] = account
                                        compensations[account_code] = account.compensation_payroll_id
                                        if not account.compensation_payroll_id:
                                            bad_compensations.append((column_num, account_code))
                                        if not account.budget_line_type_id:
                                            bad_accounts.append((column_num, account_code))
                                            is_no_line_type[(column_num, account_code)] = True
                                            has_no_line_types = True
                                    else:
                                        accounts[account_code] = False
                                        compensations[account_code] = False
                                        bad_accounts.append((column_num, account_code))
                                        is_no_line_type[(column_num, account_code)] = False
                                        has_bad_accounts = True

                        elif line_count == 2:
                            for column_num in range(len(line)):
                                columns[line[column_num]] = column_num
                        else:
                            is_personne = re.search('^\s*\d+-\d+\s*$', line[columns.get('Matricule', 1)])
                            if is_personne:
                                # No department
                                vals = {
                                    'department': line[columns.get('Department', 0)].upper(),
                                    'matricule': line[columns.get('Matricule', 1)].upper(),
                                    'nom': line[columns.get('Nom', 2)].decode(payroll.encoding).upper(),
                                    'prenom': line[columns.get('Prénom', 3)].decode(payroll.encoding).upper(),
                                    'line': line_count,
                                }
                                employee_key = vals['matricule']

                                for column_num in range(len(line)):  # Get the account data
                                    if account_header[column_num]:
                                        vals[account_header[column_num]] = get_float(line[column_num])

                                employee = employee_obj.search([('identification_id', '=', employee_key)])
                                if not employee:
                                    bad_employees.append(employee_key)
                                    vals['employee'] = False
                                else:
                                    vals['employee'] = employee

                                employee_keys.append(employee_key)
                                employee_data[employee_key] = vals
                            elif line[columns.get('Department', 0)]:
                                # There is a departement - this line should not be imported and needs to be used for the department...
                                for employee in employee_keys:
                                    if not employee_data[employee]['department']:
                                        employee_data[employee]['department'] = line[columns.get('Department', 0)]

                # Check departments
                for employee_key in employee_data.keys():
                    department = employee_data[employee_key]['department']
                    line = employee_data[employee_key]['line']
                    if department not in departments:
                        departments[department] = element_obj
                        department_budget = element_obj.search([
                            ('code', '=', department),
                            ('type', '=', 'department'),
                        ])
                        if department_budget:
                            periodic_budget = element_obj.search([
                                ('budget_department_id', '=', department_budget.id),
                                ('type', '=', 'periodic'),
                                ('date_start', '<=', payroll.period_id.date_start),
                                ('date_end', '>=', payroll.period_id.date_end),
                            ])
                            departments[department] = periodic_budget
                            if not periodic_budget:
                                is_periodics[department] = True
                                has_bad_periodics = True
                                bad_departments[department] = []
                                bad_departments[department].append('%d' % line)
                                departments[department] = periodic_budget
                        else:
                            has_bad_departments = True
                            is_periodics[department] = False
                            bad_departments[department] = []
                            bad_departments[department].append('%d' % line)
                    elif not departments[department]:
                        bad_departments[department].append('%d' % line)

                if has_bad_accounts:
                    errors += _("The following account(s) could not be found in the database:\n")
                    for (column_num, account_code) in bad_accounts:
                        if not is_no_line_type[(column_num, account_code)]:
                            column_code = convert_to_excel_letters(column_num)
                            errors += _(u"- Column %d (%s): %s\n") % (column_num, column_code, account_code)
                    errors += '\n'

                if has_no_line_types:
                    errors += _("The following account(s) are not linked to any budget line types:\n")
                    for (column_num, account_code) in bad_accounts:
                        if is_no_line_type[(column_num, account_code)]:
                            column_code = convert_to_excel_letters(column_num)
                            errors += _(u"- Column %d (%s): %s\n") % (column_num, column_code, account_code)
                    errors += '\n'

                if bad_compensations:
                    errors += _("No compensation account could be found for the following account(s):\n")
                    for (column_num, account_code) in bad_compensations:
                        column_code = convert_to_excel_letters(column_num)
                        errors += _(u"- Column %d (%s): %s\n") % (column_num, column_code, account_code)
                    errors += '\n'

                if bad_employees:
                    errors += _("The following employee(s) could not be found in the database:\n")
                    for employee in bad_employees:
                        errors += _(u"- Line %d: %s [%s, %s]\n") % (employee_data[employee]['line'], employee, employee_data[employee]['nom'], employee_data[employee]['prenom'])
                    errors += '\n'

                if multi_employees:
                    errors += _("The following employee(s) were found several times in the database:\n")
                    for employee in multi_employees:
                        errors += _(u"- Line %d: %s [%s, %s]\n") % (employee_data[employee]['line'], employee, employee_data[employee]['nom'], employee_data[employee]['prenom'])
                    errors += '\n'

                if has_bad_departments:
                    errors += _("The following department(s) could not be found in the database:\n")
                    for department in bad_departments.keys():
                        if not is_periodics[department]:
                            errors += _(u"- %s [line(s) %s]\n") % (department, ', '.join(bad_departments[department]))
                    errors += '\n'

                if has_bad_periodics:
                    errors += _("A valid period budget for following department(s) could not be found in the database:\n")
                    for department in bad_departments.keys():
                        if is_periodics[department]:
                            errors += _(u"- %s [line(s) %s]\n") % (department, ', '.join(bad_departments[department]))
                    errors += '\n'

                if not employee_data.keys():
                    errors += _("No employee was found - check the separator, maybe?\n")

                if errors:
                    new_state = 'has_errors'
                    comments += errors

                move_id = self.env['account.move']
                multi_elements = {}
                bad_elements = {}
                if not errors:
                    for employee_key in employee_data.keys():
                        employee_vals = employee_data[employee_key]
                        if employee_vals['employee']:
                            compensation_amounts = defaultdict(float)
                            employee = employee_vals['employee']
                            department = employee_vals['department']
                            budget_lines_and_detail_ids = []
                            if department in departments:
                                budget_lines_and_detail_ids = (departments[department].mapped('budget_line_ids') + departments[department].mapped('budget_line_ids.budget_detail_ids')).ids
                            for account in accounts.keys():
                                if employee_vals[account]:
                                    budget_element_id = False
                                    # TODO : Find the budget_element_id
                                    budget_element = element_obj.search([
                                        ('id', 'in', budget_lines_and_detail_ids),
                                        ('budget_line_type_id', '=', accounts[account].budget_line_type_id.id)
                                    ])
                                    if len(budget_element) == 1:
                                        budget_element_id = budget_element.id
                                    elif len(budget_element) > 1:
                                        multi_elements[(employee_key, account)] = budget_element
                                    else:
                                        bad_elements[(employee_key, account)] = True

                                    tags = get_axes(budget_element, axes)
                                    if tags:
                                        tags = ((6, 0, tuple(tags.ids)),)
                                    else:
                                        tags = ((5, 0, 0),)

                                    direction = 'debit'
                                    if employee_vals[account] < 0.0:
                                        direction = 'credit'

                                    move_line_data = {
                                        'name': 'PAIE-%s-%s' % (employee_vals['nom'], period),
                                        direction: round(abs(employee_vals[account]), 2),
                                        'company_id': payroll.company_id.id,
                                        'employee_id': employee.id,
                                        'account_id': accounts[account].id,
                                        'date': payroll.period_id.date_end,
                                    }
                                    if accounts[account].authorise_analytics:
                                        move_line_data.update({
                                            'all_tag_ids': tags,
                                            'budget_element_id': budget_element_id,
                                        })
                                    move_lines.append((0, 0, move_line_data))
                                    compensation_amounts[(compensations[account], tags)] += employee_vals[account]

                            for (compensation, tags) in compensation_amounts.keys():
                                direction = 'credit'
                                if compensation_amounts[(compensation, tags)] < 0.0:
                                    direction = 'debit'

                                move_line_data = {
                                    'name': 'PAIE-%s-%s' % (employee_vals['nom'], period),
                                    direction: round(abs(compensation_amounts[(compensation, tags)]), 2),
                                    'company_id': payroll.company_id.id,
                                    'employee_id': employee.id,
                                    'account_id': compensation.id,
                                    'date': payroll.period_id.date_end,
                                }
                                if compensation.authorise_analytics:
                                    move_line_data.update({
                                        'all_tag_ids': tags,
                                        'budget_element_id': budget_element_id,
                                    })
                                move_lines.append((0, 0, move_line_data))

                    if multi_elements or bad_elements:
                        new_state = 'has_errors'
                        if bad_elements:
                            comments += _("No budget element could be found for the following employee(s)/account(s):\n")
                            for (employee_key, account) in bad_elements.keys():
                                comments += _('- Employee %s (department %s), account %s\n') % (employee_key, employee_data[employee_key]['department'], account)
                        if multi_elements:
                            errors += _("Multiple budget elements were found for the following employee(s)/account(s):\n")
                            for (employee_key, account) in multi_elements.keys():
                                elements = multi_elements[(employee_key, account)]
                                element_list = []
                                for element in elements:
                                    element_list.append(_('%s (ID: %d)') % element.name, element.id)
                                comments += _('- Employee %s (department %s), account %s - %s\n') % (employee_key, employee_data[employee_key]['department'], account, ', '.join(element_list))

                    elif move_lines:
                        comments += _('%d move line was created.') % (len(move_lines))
                        move_id = self.env['account.move'].create({
                            'name': payroll.journal_id.sequence_id.next_by_id(),
                            'narration': _('Payroll import %s') % period,
                            'company_id': payroll.company_id.id,
                            'journal_id': payroll.journal_id.id,
                            'line_ids': move_lines,
                            'date': payroll.period_id.date_end,
                        })
                        new_state = 'imported'
                    else:
                        comments = _("No move line was created (contact IT)")
                        new_state = "has_errors"

                self.write({
                    'comments': comments,
                    'move_id': move_id.id,
                    'state': new_state,
                })

    
    def write(self, values):
        """
        If we change the file, we need to delete the account move.
        """
        if 'csv_file' in values:
            move_ids = self.mapped('move_id')
            if move_ids:
                move_ids.unlink()
            values['comments'] = False
            values['state'] = 'not_imported'
        return super(HrImportPayroll, self).write(values)

    
    def validate_move(self):
        empty = self.env['account.move']
        for payroll in self.filtered(lambda r: r.move_id != empty):
            payroll.move_id.post()
            if payroll.move_id.state == 'posted':
                payroll.state = 'done'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
