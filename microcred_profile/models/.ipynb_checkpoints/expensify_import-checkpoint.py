# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.syleam.fr/>)
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

from odoo import models, api, fields, exceptions, _
import csv
import base64
import codecs
import re
from collections import defaultdict
from odoo.exceptions import UserError


class ExpensifyImport(models.Model):
    _name = 'expensify.import'
    _description = 'Expensify Import'

    name = fields.Char(string='Name', size=64, help='The name of the export.')
    csv_file = fields.Binary(string='CSV File', help='Select the CSV file to import.')
    comments = fields.Text(string='Comments', help='The comments concerning the import', readonly=True, )
    state = fields.Selection([
        ('draft', 'Not imported'),
        ('exception', 'Has errors'),
        ('open', 'Imported'),
        ('done', 'Validated'),
    ], string='Import status', default='draft', required=True, readonly=True,
        help='The import status:\n* \'Not imported\': The file has yet to be imported.\n* \'Has errors\': The file has not been imported due to errors.\n* \'Imported\': The file has been successfully imported.\n')
    separator = fields.Selection(selection=[
        (';', '; (Semi-colon)'),
        (',', ', (Comma)'),
        ('T', '(Tabulation)'),
    ], string='Separator', help='Select the separator.', default=",", required=True, )
    encoding = fields.Selection(selection=[
        ('iso-8859-1', 'ISO-8859-1'),
        ('utf-8', 'utf-8'),
        ('windows-1252', 'Windows 1252'),
    ], string='Encoding', help='The encoding', default="windows-1252")
    move_ids = fields.One2many(comodel_name='account.move', inverse_name='expensify_id', readonly=True, string='Invoices created', help='The list of invoices linked to this Expensify import.')

    
    def treat_file(self):
        def correct_fields(dico):
            """
            This function modified the dico so as to replace tuples (id, name) with just the id
            """
            correct_fields = ['company_id', 'account_id', 'company_currency_id', 'product_id', 'currency_id', 'fiscal_position_id', 'reinvoice_distribution_id', 'partner_id', 'commercial_partner_id']
            for field in correct_fields:
                if field in dico:
                    if isinstance(dico[field], tuple):
                        dico[field] = dico[field][0]

        def correct_cr(matchobj):
            return matchobj.group(0).replace(bytes('\n',self.encoding), b' ')

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

        def find_id(xmlid, model):
            try:
                (this_id, this_model, this_resid) = self.env['ir.model.data'].xmlid_lookup(xmlid)
                if this_model == model:
                    return self.env[model].browse(this_resid)
                return False
            except:
                return False

        def create_line_string(lines):
            if len(lines) == 1:
                return(_('(line ') + lines[0] + ')')
            return(_('(lines ') + ', '.join(lines[:len(lines) - 1]) + _(' and ') + lines[-1] + ')')

        data_to_find = [
            'journal_id/id',
            'account_id/id',
            'currency_id/id',
            'company_id/id',
        ]
        data_sources = {
            'journal_id/id': ('Journal', 'journal_id', 'account.journal'),
            'account_id/id': ('Account', 'account_id', 'account.account'),
            'currency_id/id': ('Currency', 'currency_id', 'res.currency'),
            'company_id/id': ('Company', 'company_id', 'res.company'),
            'partner_id/id': ('Employee', 'partner_id', 'res.partner'),
            'product_id': ('Product (Mapping [Purpose] / [Category])', 'product_id', 'product.product'),
            'budget_id': ('Budget (Mapping [Year] / [Project] / [Departement] / [Company])', 'element_id', 'budget.element'),
        }
        required_columns = [
            'account_id/id',
            'currency_id/id',
            'journal_id/id',
            'partner_id/id',
            'company_id/id',
            'reference',
            'invoice_line_ids/name',
            'invoice_line_ids/price_unit',
            'invoice_line_ids/quantity',
            'invoice_date',
            'Purpose',
            'Category',
            'Refacturation',
            'Projets',
        ]
        copy_fields = [
            'invoice_date',
            'invoice_line_ids/name',
            'invoice_line_ids/price_unit',
            'invoice_line_ids/quantity',
            'reference',
        ]
        invoice_fields = [
            'id',
            'account_id/id',
            'currency_id/id',
            'journal_id/id',
            'employee',
            'company_id/id',
            'reference',
            'invoice_date',
        ]
        ExpensifyProduct = self.env['expensify.product']
        ExpensifyBudget = self.env['expensify.budget']
        Employee = self.env['hr.employee']
        AccountInvoice = self.env['account.move']
        AccountInvoiceLine = self.env['account.move.line']
        BudgetElement = self.env['budget.element']
        view_id = self.env.ref('microcred_profile.invoice_supplier_microcred_tree', False).id

        invoices_created = AccountInvoice

        for expensify in self:
            expensify.move_ids.filtered(lambda r: r.state == 'validated').write({'state': 'draft'})  # Put the validated invoices to draft
            if expensify.move_ids.filtered(lambda r: r.state != 'draft'):
                # We can't delete some invoices - can't retreat ! Normally, we should not be in this state...
                raise UserError(_('In order to retreat the file, the old invoices have to be deleted but some of the old invoices are not in a draft state. As a result, the file cannot be retreated.'))

            expensify.move_ids.unlink()
            separator = str(expensify.separator)
            if separator == 'T':
                separator = '\t'

            errors = []
            this_file = base64.decodestring(expensify.csv_file)
            #this_file = base64.b64encode(expensify.csv_file)
            this_file = re.sub(bytes('"\"[^\"]*\""',self.encoding),correct_cr, this_file) 
            this_file = this_file.split(b'\n')
            
            reader = csv.DictReader(codecs.iterdecode(this_file,self.encoding),delimiter=separator, quotechar='"')
            
            missing_fields = []
            for fieldname in required_columns:
                if fieldname not in reader.fieldnames:
                    missing_fields.append(fieldname)
                id_field = 'id'
                if id_field not in reader.fieldnames:
                    id_field = bytes('\xef\xbb\xbfid',self.encoding)
                if id_field not in reader.fieldnames:
                     missing_fields.append('id')

            if missing_fields:
                #This is too important to continue...
                if len(missing_fields) > 1:
                    errors.append(_('The following columns are missing in the file:'))
                else:
                    errors.append(_('The following column is missing in the file:'))

                for field in missing_fields:
                    errors.append('- {field}'.format(field=field))
                expensify.write({
                    'comments': '\n'.join(errors),
                    'state': 'exception'
                })

            else:
                line_count = 0
                data_lines = []
                invoice_data = defaultdict(dict)
                invoices_found = defaultdict(list)
                data_not_found = defaultdict(list)
                type_not_found = defaultdict(dict)
                bad_dates = defaultdict(list)
                bad_floats = defaultdict(list)
                no_address = {}
                no_departments = {}

                # Check data prior to importing
                for line in reader:
                    # Encode the fields
                    try:
                        for field in reader.fieldnames:
                            line[field] = str(line[field],encoding = self.encoding)
                    except:
                         errors = []  # This error is more important than the rest
                         errors.append(_('Please check the encoding - the one selected cannot be used...'))
                         break 

                    data_line = {}
                    line_count += 1
                    invoice = find_id(line[id_field], 'account.move')
                    if invoice:
                        invoices_found[line[id_field]].append(str(line_count))

                    data_line['id'] = line[id_field]

                    company = False
                    for data_type in data_to_find:
                        data = find_id(line[data_type], data_sources[data_type][2])
                        if not data:
                            data_not_found[(data_type, line[data_type])].append(str(line_count))
                            type_not_found[data_type][line[data_type]] = True
                        else:
                            data_line[data_type] = data
                            if data_type == 'company_id/id':
                                company = data

                    employee = Employee.search([('identification_id', '=', line['partner_id/id'])])
                    data_line['employee'] = employee
                    budget = False
                    if not employee:
                        data_not_found[('partner_id/id', line['partner_id/id'])].append(str(line_count))
                        type_not_found['partner_id/id'][line['partner_id/id']] = True
                    else:
                        if not employee.address_id:
                            no_address[employee] = True
                        if not employee.department_id:
                            no_departments[employee] = True
                        else:
                            year = line['invoice_date'][:4]
                            if not year.isdigit():
                                bad_dates[line['invoice_date']].append(str(line_count))
                            else:
                                budget = ExpensifyBudget.get_budget(int(year), line['Projets'], company, employee=employee)
                                if not budget:
                                    label = u'[{year}] / [{project}] / [{employee.department_id.name}] / [{company.name}]'.format(year=year, project=line['Projets'], employee=employee, company=company)
                                    data_not_found[('budget_id', label)].append(str(line_count))
                                    type_not_found['budget_id'][label] = True
                                else:
                                    data_line['budget'] = budget

                    product = ExpensifyProduct.get_product(line['Purpose'], line['Category'], company)
                    if not product:
                        label = u'[{purpose}] / [{category}]'.format(purpose=line['Purpose'], category=line['Category'])
                        data_not_found[('product_id', label)].append(str(line_count))
                        type_not_found['product_id'][label] = True
                    else:
                        data_line['product'] = product

                    try:
                        value = float(line['invoice_line_ids/price_unit'])
                        line['invoice_line_ids/price_unit'] = value
                    except:
                        bad_floats[line['invoice_line_ids/price_unit']].append(str(line_count))
                    try:
                        value = float(line['invoice_line_ids/quantity'])
                        line['invoice_line_ids/quantity'] = value
                    except:
                        bad_floats[line['invoice_line_ids/quantity']].append(str(line_count))

                    reinvoice = False
                    if line.get('Refacturation'):
                        reinvoice = BudgetElement.search([('expensify_code', '=', line['Refacturation'])]).id
                    data_line['remove_id'] = reinvoice

                    # Add other fields (not requiring verificaton)
                    for field in copy_fields:
                        data_line[field] = line[field]

                    data_lines.append(data_line)
                    for field in invoice_fields:
                        if field in data_line:
                            invoice_data[data_line['id']][field] = data_line[field]

                if invoices_found:
                    if errors:
                        errors.append('')
                    if len(invoices_found.keys()) > 1:
                        errors.append(_('The following invoices have already been imported:'))
                    else:
                        errors.append(_('The following invoice has already been imported:'))

                    for invoice in invoices_found.keys():
                        errors.append(_(u'- {invoice} {lines}').format(invoice=invoice, lines=create_line_string(invoices_found[invoice])))

                if data_not_found:
                    for data_type in type_not_found.keys():
                        if errors:
                            errors.append('')
                        errors.append(_(u'The following data for {data} has not been found:').format(data=data_sources[data_type][0]))
                        for value in type_not_found[data_type]:
                            errors.append(_(u'- {value} {lines}').format(value=value, lines=create_line_string(data_not_found[(data_type, value)])))

                if bad_floats:
                    if errors:
                        errors.append('')
                    if len(bad_floats.keys()) > 1:
                        errors.append(_('The following numbers are not decimals:'))
                    else:
                        errors.append(_('The following number is not decimal:'))

                    for number in bad_floats:
                        errors.append(_(u'- \'{number}\' {lines}').format(number=number, lines=create_line_string(bad_floats[number])))

                if bad_dates:
                    if errors:
                        errors.append('')
                    if len(bad_dates.keys()) > 1:
                        errors.append(_('The following dates could not be decoded to deduce the year:'))
                    else:
                        errors.append(_('The following date could not be decoded to deduce the year:'))

                    for date in bad_dates:
                        errors.append(_(u'- \'{date}\' {lines}').format(date=date, lines=create_line_string(bad_dates[date])))

                if no_address:
                    if errors:
                        errors.append('')
                    if len(no_address.keys()) > 1:
                        errors.append(_('Partners have not been defined for the following employees:'))
                    else:
                        errors.append(_('A partner has not been defined for the following employee:'))

                    for employee in no_address:
                        errors.append(_(u'- {employee.identification_id}, ({employee.name})').format(employee=employee))

                if no_departments:
                    if errors:
                        errors.append('')
                    if len(no_departments.keys()) > 1:
                        errors.append(_('The following employees have no departments:'))
                    else:
                        errors.append(_('The following employee has no department:'))

                    for employee in no_departments:
                        errors.append(_(u'- {employee.identification_id}, ({employee.name})').format(employee=employee))

            if errors:
                expensify.write({
                    'comments': '\n'.join(errors),
                    'state': 'exception'
                })
                continue

            # Everything is ok... Create the invoices
            for move_id in invoice_data:
                invoice_header = invoice_data[move_id]
                invoice_line_amounts = defaultdict(float)
                invoice_lines = []
                sage_name = _('Exp: {partner.name}').format(partner=invoice_header['employee'])
                for line in data_lines:
                    if line['id'] == move_id:
                        key = (line['product'], line['budget'], line.get('remove_id'))
                        invoice_line_amounts[key] += line['invoice_line_ids/price_unit'] * line['invoice_line_ids/quantity']

                for (product, budget, reinvoice) in invoice_line_amounts:
                    invoice_line = {
                        'product_id': product.id,
                        'name': sage_name,
                        'price_unit': invoice_line_amounts[(product, budget, reinvoice)],
                        'quantity': 1.0,
                        'budget_element_id': budget.id,
                    }
                    if reinvoice:
                        # Create a new distribution for this line (the create copies the budget element's distribution if none is supplied)
                        invoice_line['distribution_cost_ids'] = [(0, 0, {
                            'child_id': reinvoice,
                            'percentage': 100.0,
                        })]
                    invoice_lines.append((0, 0, invoice_line))

                view_info = AccountInvoice.fields_view_get(view_id=view_id, view_type='form')  # view_id=invoice_pay_info['view_id'], view_type=invoice_pay_info['view_type'])
                fields = view_info['fields'].keys()
                new_invoice_data = dict.fromkeys(fields, False)
                new_invoice_data.update(AccountInvoice.default_get(fields))
                onchange_spec = AccountInvoice._onchange_spec(view_info)
                new_invoice_data.update(AccountInvoice.onchange(new_invoice_data, new_invoice_data.keys(), onchange_spec)['value'])

                new_invoice_data.update({
                    'partner_id': invoice_header['employee'].address_id.id,
                    'account_id': invoice_header['account_id/id'].id,
                    'journal_id': invoice_header['journal_id/id'].id,
                    'currency_id': invoice_header['currency_id/id'].id,
                    'company_id': invoice_header['company_id/id'].id,
                    'reference': invoice_header['reference'],
                    'invoice_date': invoice_header['invoice_date'],
                    'sage_name': sage_name,
                    'type': 'in_invoice',
                    'expensify_id': expensify.id,
                    'attachment_required': False,
                })

                onchange_spec = AccountInvoice._onchange_spec(view_info)
                new_invoice_data.update(AccountInvoice.onchange(new_invoice_data, new_invoice_data.keys(), onchange_spec)['value'])
                new_invoice_data.update({
                    'invoice_line_ids': invoice_lines,
                })

                correct_fields(new_invoice_data)

                new_lines = []
                for line in new_invoice_data['invoice_line_ids']:
                    if line[0] == 0:
                        correct_fields(line[2])

                        if not line[2].get('account_id') and line[2].get('product_id'):
                            product = self.env['product.product'].browse(line[2]['product_id'])
                            fpos = self.env['account.fiscal.position'].browse(new_invoice_data.get('fiscal_position_id'))
                            company = self.env['res.company'].browse(line[2].get('company_id') or new_invoice_data.get('company_id'))
                            account = AccountInvoiceLine.get_invoice_line_account(type, product, fpos, company)
                            if account:
                                line[2]['account_id'] = account.id

                            # Set taxes as well
                            taxes = product.taxes_id or account.tax_ids

                            # Keep only taxes of the company
                            company_id = company or self.env.user.company_id
                            taxes = taxes.filtered(lambda r: r.company_id == company_id)

                            line[2]['tax_ids'] = [(6, 0, fpos.map_tax(taxes).mapped('id'))]
                            line[2]['name'] = sage_name

                    new_lines.append(line)

                new_invoice_data.update({
                    'invoice_line_ids': new_lines,
                    'expensify_id': expensify.id,
                    'sage_name': sage_name,
                })

                new_invoice = AccountInvoice.create(new_invoice_data)
                """
                Create an XML ID as well
                """
                xml_vals = {
                    'model': 'account.move',
                    'res_id': new_invoice.id,
                    'module': 'expensify',
                    'name': move_id[10:],
                }
                self.env['ir.model.data'].create(xml_vals)
                invoices_created |= new_invoice

            expensify.write({
                'comments': False,
                'state': 'open'
            })
            continue

        if invoices_created:
            action = self.env.ref('account.action_invoice_tree2', False)
            action_data = action.read()[0]

            action_data.update(
                domain=[('id', 'in', invoices_created.ids)],
                context={
                    'target': 'new',
                }
            )
            return action_data


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
