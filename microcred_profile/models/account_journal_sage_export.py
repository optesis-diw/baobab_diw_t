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

import csv
from datetime import datetime
from io import StringIO
from odoo import models, api, fields
import base64
from odoo.tools.translate import _
from odoo.tools import float_round, float_is_zero
from collections import defaultdict


class AccountJournalSageExport(models.Model):
    _name = "account.journal.sage.export"
    _description = "Account journal Sage export"
    _order = "date_export desc"

    date_export = fields.Datetime(string='Export date', help='The date of the last export.')
    export_file = fields.Binary(string='Export file', help='The exported file.')
    filename = fields.Char(string='Filename', size=64, help='The name of the file')
    journal_id = fields.Many2one('account.journal', string='Journal', help='The journal exported.')
    date_from = fields.Date(string='Date from', help='The date from which the account move lines are taken into account.')
    date_to = fields.Date(string='Date to', help='The date up to which the account move lines are taken into account.')
    name = fields.Char(string='Name', size=64, compute='_get_name')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', help='The company.', related='journal_id.company_id', store=True)

    @api.onchange('journal_id')
    def _change_journal_id(self):
        self.update({
            'company_id': self.journal_id.company_id.id
        })

    
    def _get_name(self):
        for export in self:
            export.name = _('%s [%s]') % (export.date_export, export.journal_id.code or export.journal_id.name)

    
    def generate_file(self):

        def create_tag_name(tags):
            name = ''
            for tag in tags:
                name += tag
            return name

        self.ensure_one()
        journal_code = self.journal_id.sage_code or self.journal_id.code

        csv_file = StringIO()
        csv_writer = csv.DictWriter(csv_file, fieldnames=[
            'Code journal',
            'Date',
            'N piece',
            'Numero facture',
            'N compte general',
            'Type norme',
            'N compte tiers',
            'N plan analytique',
            'N section 1',
            'Libelle Decriture',
            'Montant',
            'Sens',
            'Reference',
        ], delimiter=';')

        domain = [
            ('journal_id', '=', self.journal_id.id),
            ('export_id', '=', False),
        ]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        lines = self.env['account.move.line'].search(domain)

        if not lines:
            return False

        axes = self.env['account.axis'].search([('sage_export', '=', True), ('company_id', '=', self.company_id.id)])

        for line in lines:
            if line.parent_state != 'cancel': 
                if line.parent_state != 'draft':
                    ref = "odoo_%s" % line.id
                    invoice = (line.move_id or
                           self.env['account.move'].search([('move_id', '=', line.move_id.id)]) or
                           False)
                    move_name = str(line.move_id.name or '')
                    move_ref = str(invoice and
                                       invoice.ref or
                                       line.move_id.name or '')
                    line_name = str(line.name or '')
                    num_invoice = str((self.journal_id.type in ('sale', 'purchase') and
                                    line.move_id.ref) or '')
                    partner_name = ''
                    if line.account_id.export_thirdparty_account:
                        partner_name = str(line.partner_id.thirdparty_account or
                                               _('Unknown'))
                    entry_label = str(line.name or '')
                    account_code = str(line.account_id.code or '')
                    line_dico = {
                        'Code journal': journal_code,
                        'Date': datetime.strftime(fields.Date.to_date(line.date), '%Y%m%d'),
                        'N piece': move_name,
                        'Numero facture': num_invoice,
                        'N compte general': account_code,
                        'Type norme': 'G',
                        'N compte tiers': partner_name,
                        'N plan analytique': '',
                        'N section 1': '',
                        'Libelle Decriture': entry_label,
                        'Montant': ("%.2f" % (line.credit or line.debit or 0)).replace('.', ','),
                        'Sens': line.debit > 0 and 'D' or 'C',
                        'Reference': ref + " " + move_ref + " " + line_name,
                    }

                    csv_writer.writerow(line_dico)

                    # Write the analytical lines
                    line_dico.update({
                        'Type norme': 'A',
                        'N compte tiers': '',
                    })
                    for axis in axes:
                        order = 'subgroup'
                        if axis.export_reverse:
                            order = 'subgroup desc'

                        if axis.reinvoice:
                            # These are split into one line per reinvoice
                            for distribution in line.distribution_partner_ids:
                                reinvoice_tags = line.all_tag_ids.search([
                                    ('id', 'in',
                                     distribution.budget_partner_id.get_tags(axis.number).ids)], order=order)
                                reinvoice_name = ''
                                if reinvoice_tags:
                                    reinvoice_name = create_tag_name([x.name for x in reinvoice_tags])
                                line_dico.update({
                                    'N plan analytique': 4,
                                    'N section 1': reinvoice_name,
                                    'Montant': ("%.2f" % (distribution.amount_fixed)).replace('.', ','),
                                    'Reference': ref + '_%d' % distribution.id + " " + move_ref + " " + line_name,
                                })
                                csv_writer.writerow(line_dico)
                        else:
                            # A regular line
                            line_tags = line.all_tag_ids.filtered(lambda r: r.axis_id == axis)
                            if line_tags:
                                line_tags = line_tags.search([('id', 'in', line_tags.ids)], order=order)
                                line_dico.update({
                                    'N plan analytique': axis.number,
                                    'N section 1': create_tag_name([x.name for x in line_tags]),
                                    'Montant': ("%.2f" % (line.credit or line.debit or 0)).replace('.', ','),
                                    'Reference': ref + " " + move_ref + " " + line_name,
                                })
                                csv_writer.writerow(line_dico)
                            elif axis.budget_split:
                                # Get the tags from the budget element
                                main_budget = line.budget_element_id
                                while main_budget and not main_budget.distribution_budget_ids:
                                    main_budget = main_budget.budget_id

                                if main_budget:
                                    amount = float_round(line.credit or line.debit, precision_digits=2)
                                    remaining = amount
                                    tag_amounts = defaultdict(float)
                                    tag_distributions = defaultdict(list)
                                    for distribution in main_budget.distribution_budget_ids:
                                        split_tags = distribution.child_id.get_tags(axis.number)
                                        if split_tags:
                                            split_tags.ensure_one()
                                            percentage = distribution.percentage
                                            if distribution.amount_fixed:
                                                percentage = distribution.equivalent_percentage

                                            this_amount = float_round((amount * percentage) / 100.0, precision_digits=2)
                                            tag_amounts[split_tags] += this_amount
                                            tag_distributions[split_tags].append(str(distribution.id))
                                            remaining -= this_amount

                                    # Apply any residual (rounding error) to the largest one
                                    if not float_is_zero(remaining, precision_digits=2):
                                        max_tag_id = False
                                        max_tag_amount = 0.0
                                        for tag in tag_amounts:
                                            if tag_amounts[tag] > max_tag_amount:
                                                max_tag_amount = tag_amounts[tag]
                                                max_tag_id = tag
                                        if max_tag_id:
                                            tag_amounts[max_tag_id] += remaining

                                    for tag in tag_amounts:
                                        line_dico.update({
                                            'N plan analytique': axis.number,
                                            'N section 1': create_tag_name([x.name for x in tag]),
                                            'Montant': ("%.2f" % (tag_amounts[tag])).replace('.', ','),
                                            'Reference': ref + '_%s' % ','.join(
                                                tag_distributions[tag.id]) + " " + move_ref + " " + line_name,
                                        })
                                        csv_writer.writerow(line_dico)


        vals = {
            'date_export': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'export_file': base64.b64encode(csv_file.getvalue().encode("utf16")),
#             'export_file': base64.encodebytes(csv_file.getvalue().encode()),
            'filename': _('Sage_Export_%s_%s.csv') % (journal_code, datetime.now().strftime('%Y-%m-%d_%H-%M-%S')),
        }
        self.write(vals)
        self.journal_id.date_last_export = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines.write({
            'export_id': self.id,
        })
        return True

    
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
