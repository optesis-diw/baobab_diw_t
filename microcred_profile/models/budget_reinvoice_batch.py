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

from odoo import models, api, fields, _
from datetime import datetime


class BudgetReinvoiceBatch(models.Model):
    _name = 'budget.reinvoice.batch'
    _description = 'Budget reinvoice batch'

    @api.model
    def _get_default_company(self):
        ret = self.env.context.get('force_company')
        if ret:
            return self.env['res.company'].browse(ret)
        return self.env.user.company_id

    name = fields.Char(string='Name',  help='Batch name')
    date_batch = fields.Datetime(string='Batch date', help='The date the batch was executed.', copy=False)
    date_from = fields.Date(string='Date from', help='The date from which tbe account movement lines are taken into account.')
    date_to = fields.Date(string='Date to', help='The date up to which tbe account movement lines are taken into account.')
    partner_ids = fields.Many2many('budget.element', string='Partners to invoice', help='Select the partners to invoice.', domain=[('type', '=', 'partner'), ('reinvoiceable', '=', True)])
    distribution_ids = fields.One2many('account.move.line.distribution', 'reinvoice_batch_id', string='Partner distribution lines', help='The partner distribution lines in this reinvoice batch.')
    move_line_ids = fields.Many2many('account.move.line', string='Move lines', help='The move lines taken into account.', compute='_get_move_lines', )
    move_ids = fields.One2many('account.move', 'reinvoice_batch_id', string='Invoices', help='The invoice created in this batch.', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', help='Select the company.', required=True, default=_get_default_company)

    
    def _get_move_lines(self):
        for batch in self:
            batch.move_line_ids = batch.mapped('distribution_ids.move_line_id.id')

    @api.model
    def correct_fields(self, dico):
        """
        This function modified the dico so as to replace tuples (id, name) with just the id
        """
        correct_fields = ['company_id', 'account_id', 'company_currency_id', 'product_id', 'currency_id', 'fiscal_position_id', 'reinvoice_distribution_id']
        for field in correct_fields:
            if field in dico:
                if isinstance(dico[field], tuple):
                    dico[field] = dico[field][0]

    
    def execute_batch(self):
        """
        Generate invoices for selected partners, in the dates provided, based on account move lines
        """
        invoice_obj = self.env['account.move']
        invoice_line_obj = self.env['account.move.line']

        new_ids = []

        view_id = self.env.ref('account.move_form', False).id

        move_ids = self.env['account.move']  # List of purchase invoices whose reinvoiced amounts need to be updated
        move_lines = self.env['account.move.line']
        for batch in self:
            main_domain = [
                ('reinvoice_batch_id', '=', False),
                ('amount_fixed', '>', 0.0),
                ('move_line_id.company_id', '=', batch.company_id.id),
            ]
            if batch.date_from:
                main_domain.append(('move_line_id.date', '>=', batch.date_from))
            if batch.date_to:
                main_domain.append(('move_line_id.date', '<=', batch.date_to))

            # Create invoices for each partner
            partners = self.env.context.get('partners', batch.partner_ids)
            for partner in partners:
                domain = main_domain + [('budget_partner_id', '=', partner.id)]
                distributions = self.env['account.move.line.distribution'].search(domain)

                invoice_lines = []
                for distribution in distributions:
                    move_lines |= distribution.move_line_id
                    product = distribution.move_line_id.product_id or distribution.asset_line_id.asset_id.invoice_line_id.product_id
                    invoice_lines.append((0, 0, {
                        'product_id': product.id,
                        'quantity': 1.0,
                        'price_unit': distribution.amount_fixed,
                        'name': distribution.move_line_id.name,
                        'reinvoice_distribution_id': distribution.id,
                        'company_id': batch.company_id.id,
                        'currency_id': batch.company_id.currency_id.id,
                    }))
                    if distribution.move_line_id.move_id:
                        move_ids |= distribution.move_line_id.move_id

                view_info = invoice_obj.fields_view_get(view_id=view_id, view_type='form')  # view_id=invoice_pay_info['view_id'], view_type=invoice_pay_info['view_type'])
                fields = view_info['fields'].keys()
                invoice_data = dict.fromkeys(fields, False)
                invoice_data.update(invoice_obj.default_get(fields))
                invoice_data.update({
                    'type': 'out_invoice',
                })
                onchange_spec = invoice_obj._onchange_spec(view_info)
                invoice_data.update(invoice_obj.onchange(invoice_data, invoice_data.keys(), onchange_spec)['value'])

                invoice_data.update({
                    'type': 'out_invoice',
                    'reinvoice_batch_id': batch.id,
                    'partner_id': partner.partner_id.id,
                    'invoice_line_ids': invoice_lines,
                    'name': _('Invoice - %s - %s') % (partner.partner_id.name, batch.name),
                    'origin': batch.name,
                    'company_id': batch.company_id.id,
                    'currency_id': batch.company_id.currency_id.id,
                })

                onchange_spec = invoice_obj._onchange_spec(view_info)
                invoice_data.update(invoice_obj.onchange(invoice_data, invoice_data.keys(), onchange_spec)['value'])

                self.correct_fields(invoice_data)

                new_lines = []
                for line in invoice_data['invoice_line_ids']:
                    if line[0] == 0:
                        self.correct_fields(line[2])

                        if not line[2].get('account_id') and line[2].get('product_id'):
                            product = self.env['product.product'].browse(line[2]['product_id'])
                            fpos = self.env['account.fiscal.position'].browse(invoice_data.get('fiscal_position_id'))
                            company = self.env['res.company'].browse(line[2].get('company_id') or invoice_data.get('company_id'))
                            account = invoice_line_obj.get_invoice_line_account(invoice_data['type'], product, fpos, company)
                            if account:
                                line[2]['account_id'] = account.id

                            # Set taxes as well
                            taxes = product.taxes_id or account.tax_ids

                            # Keep only taxes of the company
                            company_id = company or self.env.user.company_id
                            taxes = taxes.filtered(lambda r: r.company_id == company_id)

                            line[2]['tax_ids'] = [(6, 0, fpos.map_tax(taxes).mapped('id'))]

                        if line[2].get('reinvoice_distribution_id'):
                            distribution = self.env['account.move.line.distribution'].browse(line[2]['reinvoice_distribution_id'])
                            line[2]['name'] += '\n' + _('%.2f%% supported by the subsidiary') % ((100.0 * line[2]['price_unit']) /
                                                                                                 (distribution.move_line_id.credit or distribution.move_line_id.debit or 0.001))

                    new_lines.append(line)

                invoice_data.update({
                    'invoice_line_ids': new_lines,
                    'reinvoice_batch_id': batch.id,
                    'name': _('Invoice - %s - %s') % (partner.partner_id.name, batch.name),
                    'origin': batch.name,
                    'invoice_date': batch.date_to,
                    'company_id': batch.company_id.id,
                    'currency_id': batch.company_id.currency_id.id,
                })

                new_id = invoice_obj.create(invoice_data)
                for distribution in distributions:
                    distribution_vals = {
                        'reinvoice_batch_id': batch.id,
                        'reinvoice_invoice_line_id': invoice_line_obj.search([('reinvoice_distribution_id', '=', distribution.id)]).id
                    }
                    distribution.write(distribution_vals)

                new_ids.append(new_id.id)

        self.write({
            'date_batch': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        if move_ids:
            move_ids.calculate_reinvoiced_amount()

        if move_lines:
            move_lines.calculate_reinvoiced_amount()

        if new_ids:
            action = self.env.ref('account.action_invoice_tree1', False)
            action_data = action.read()[0]

            action_data.update(
                domain=[('id', 'in', new_ids)],
                context={
                    'target': 'new',
                }
            )

            return action_data

    
    def reexecute_batch(self):
        """
        Update all invoices linked to this batch
        """
        # Add any missing partner invoices
        invoice_obj = self.env['account.move']
        view_id = self.env.ref('account.move_form', False).id

        for batch in self:
            for partner in batch.partner_ids:
                partner_invoice = self.move_ids.filtered(lambda r: r.partner_id.id == partner.partner_id.id and r.state == 'draft')
                if not partner_invoice:
                    view_info = invoice_obj.fields_view_get(view_id=view_id, view_type='form')  # view_id=invoice_pay_info['view_id'], view_type=invoice_pay_info['view_type'])
                    fields = view_info['fields'].keys()
                    invoice_data = dict.fromkeys(fields, False)
                    invoice_data.update(invoice_obj.default_get(fields))
                    onchange_spec = invoice_obj._onchange_spec(view_info)
                    invoice_data.update(invoice_obj.onchange(invoice_data, invoice_data.keys(), onchange_spec)['value'])

                    invoice_data.update({
                        'type': 'out_invoice',
                        'reinvoice_batch_id': batch.id,
                        'partner_id': partner.partner_id.id,
                        'name': _('Invoice - %s - %s') % (partner.partner_id.name, batch.name),
                        'invoice_date': batch.date_to,
                        'origin': batch.name,
                    })

                    onchange_spec = invoice_obj._onchange_spec(view_info)
                    invoice_data.update(invoice_obj.onchange(invoice_data, invoice_data.keys(), onchange_spec)['value'])

                    self.correct_fields(invoice_data)

                    invoice_obj.create(invoice_data)

        self.update_batch_invoice(self.mapped('move_ids'))
        for batch in self:
            partners_invoiced = batch.mapped('move_ids').filtered(lambda r: r.state == 'draft').mapped('partner_id')
            budget_partners_to_invoice = self.env['budget.element']
            for budget_partner in batch.partner_ids:
                if budget_partner.partner_id not in partners_invoiced:
                    budget_partners_to_invoice |= budget_partner
            if budget_partners_to_invoice:
                batch.with_context({'partners': budget_partners_to_invoice}).execute_batch()

        self.write({
            'date_batch': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    
    def update_batch_invoice(self, invoices):
        """
        Update invoice(s) with data lines
        """

        invoice_obj = self.env['account.move']
        invoice_line_obj = self.env['account.move.line']
        view_id = self.env.ref('account.move_form', False).id

        partner_ids = invoices.mapped('partner_id.id')
        partner_map = {}
        for budget_partner in self.env['budget.element'].search([('partner_id', 'in', partner_ids), ('type', '=', 'partner')]):
            partner_map[budget_partner.partner_id] = budget_partner.id

        move_ids = self.env['account.move']  # List of purchase invoices whose reinvoiced amounts need to be updated
        move_lines = self.env['account.move.line']
        for invoice in invoices:
            if not invoice.invoice_date:
                invoice.invoice_date = invoice.reinvoice_batch_id.date_to

            domain = [
                ('budget_partner_id', '=', partner_map[invoice.partner_id]),
                ('amount_fixed', '>', 0.0),
                ('move_line_id.company_id', '=', invoice.company_id.id),
            ]
            if invoice.reinvoice_batch_id.date_from:
                domain.append(('move_line_id.date', '>=', invoice.reinvoice_batch_id.date_from))
            if invoice.reinvoice_batch_id.date_to:
                domain.append(('move_line_id.date', '<=', invoice.reinvoice_batch_id.date_to))

            distributions = self.env['account.move.line.distribution'].search(domain)

            new_invoice_lines = []
            for distribution in distributions:
                if not distribution.reinvoice_invoice_line_id:  # Need to create a new line
                    move_lines |= distribution.move_line_id
                    product = distribution.move_line_id.product_id or distribution.asset_line_id.asset_id.invoice_line_id.product_id
                    new_invoice_lines.append((0, 0, {
                        'product_id': product.id,
                        'quantity': 1.0,
                        'price_unit': distribution.amount_fixed,
                        'name': distribution.move_line_id.name,
                        'reinvoice_distribution_id': distribution.id,
                        'company_id': invoice.company_id.id,
                        'currency_id': invoice.company_id.currency_id.id,
                    }))
                else:  # Update the existing line with the amount (just in case it changed)
                    distribution.reinvoice_invoice_line_id.price_unit = distribution.amount_fixed

                if distribution.move_line_id.move_id:
                    move_ids |= distribution.move_line_id.move_id

            # Remove any invoice lines that are not to be found in the distribution list (changed partner, for example)
            for invoice_line in invoice.invoice_line_ids:
                if invoice_line.reinvoice_distribution_id not in distributions:
                    invoice_line.unlink()

            if new_invoice_lines:  # Create a new, fake invoice so that the lines can be created for the existing invoice
                view_info = invoice_obj.fields_view_get(view_id=view_id, view_type='form')  # view_id=invoice_pay_info['view_id'], view_type=invoice_pay_info['view_type'])
                fields = view_info['fields'].keys()
                invoice_data = dict.fromkeys(fields, False)
                invoice_data.update(invoice.default_get(fields))
                onchange_spec = invoice_obj._onchange_spec(view_info)
                invoice_data.update(invoice_obj.onchange(invoice_data, invoice_data.keys(), onchange_spec)['value'])

                invoice_data.update({
                    'type': 'out_invoice',
                    'reinvoice_batch_id': invoice.reinvoice_batch_id.id,
                    'partner_id': invoice.partner_id.id,
                    'invoice_line_ids': new_invoice_lines,
                    'company_id': invoice.company_id.id,
                    'currency_id': invoice.company_id.currency_id.id,
                })

                onchange_spec = invoice_obj._onchange_spec(view_info)
                invoice_data.update(invoice_obj.onchange(invoice_data, invoice_data.keys(), onchange_spec)['value'])

                self.correct_fields(invoice_data)

                for line in invoice_data['invoice_line_ids']:
                    if line[0] == 0:
                        self.correct_fields(line[2])

                        if not line[2].get('account_id') and line[2].get('product_id'):
                            product = self.env['product.product'].browse(line[2]['product_id'])
                            fpos = self.env['account.fiscal.position'].browse(invoice_data.get('fiscal_position_id'))
                            company = self.env['res.company'].browse(line[2].get('company_id') or invoice_data.get('company_id'))
                            account = invoice_line_obj.get_invoice_line_account(invoice_data['type'], product, fpos, company)
                            if account:
                                line[2]['account_id'] = account.id

                            # Set taxes as well
                            taxes = product.taxes_id or account.tax_ids

                            # Keep only taxes of the company
                            company_id = company or self.env.user.company_id
                            taxes = taxes.filtered(lambda r: r.company_id == company_id)

                            line[2]['tax_ids'] = [(6, 0, fpos.map_tax(taxes).mapped('id'))]

                        if line[2].get('reinvoice_distribution_id'):
                            distribution = self.env['account.move.line.distribution'].browse(line[2]['reinvoice_distribution_id'])
                            line[2]['name'] += '\n' + _('%.2f%% supported by the subsidiary') % ((100.0 * line[2]['price_unit']) / (distribution.move_line_id.credit or distribution.move_line_id.debit or 0.001))

                        line[2]['move_id'] = invoice.id
                        invoice_line_obj.create(line[2])
            else:  # Update the invoice
                invoice._onchange_invoice_line_ids()

            for distribution in distributions:
                invoice_line_id = invoice_line_obj.search([('reinvoice_distribution_id', '=', distribution.id)]).ids
                if invoice_line_id:
                    invoice_line_id = invoice_line_id[0]
                distribution_vals = {
                    'reinvoice_batch_id': self.id,
                    'reinvoice_invoice_line_id': invoice_line_id,
                }
                distribution.write(distribution_vals)

        if move_ids:
            move_ids.calculate_reinvoiced_amount()

        if move_lines:
            move_lines.calculate_reinvoiced_amount()

    
    def unlink(self):
        """
        Delete the created invoices as well
        """
        self.mapped('move_ids').unlink()
        return super(BudgetReinvoiceBatch, self).unlink()

    
    def write(self, vals):
        """
        If a partner is removed, delete its corresponding invoice.
        """
        ret = super(BudgetReinvoiceBatch, self).write(vals)
        if 'partner_ids' in vals:
            for batch in self:
                partners_ok = []
                for budget_partner in batch.partner_ids:
                    partners_ok.append(budget_partner.partner_id)

                for invoice in batch.move_ids:
                    if invoice.partner_id not in partners_ok:
                        invoice.unlink()

        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
