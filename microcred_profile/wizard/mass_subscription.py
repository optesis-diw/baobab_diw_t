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
from odoo.tools.translate import _
from odoo.exceptions import UserError


class WizardMassSubscription(models.TransientModel):
    _name = 'wizard.mass.subscription'
    _description = 'Mass subscription wizard'

    partner_ids = fields.Many2many(comodel_name='res.partner', string='Partners', help='Select the partner(s) to subscribe')
    move_ids = fields.Many2many(comodel_name='account.move', string='Invoice(s)', help='The invoice(s) be subscribed to.')
    purchase_ids = fields.Many2many(comodel_name='purchase.order', string='Purchase order(s)', help='The purchase(s) be subscribed to.')
    element_ids = fields.Many2many(comodel_name='budget.element', string='Budget element(s)', help='The budget element(s) be subscribed to.')
    no_invoices = fields.Boolean(string='No invoices', default=True)
    no_purchases = fields.Boolean(string='No purchases', default=True)
    no_elements = fields.Boolean(string='No elements', default=True)
    is_ok = fields.Boolean(string='Is ok')

    @api.onchange('partner_ids')
    def change_partners(self):
        self.is_ok = len(self.partner_ids) > 0

    @api.model
    def default_get(self, fields_list):
        """
        Get the invoice(s)/purchase order(s) or budget element(s)
        """

        values = super(WizardMassSubscription, self).default_get(fields_list)

        if self.env.context.get('active_ids'):
            ids = [(6, 0, self.env.context.get('active_ids'))]
            model = self.env.context.get('active_model')
            if model == 'budget.element':
                values['element_ids'] = ids
                values['no_elements'] = False
            elif model == 'account.move':
                values['move_ids'] = ids
                values['no_invoices'] = False
            elif model == 'purchase.order':
                values['purchase_ids'] = ids
                values['no_purchases'] = False
            else:
                raise UserError(_('The model type \'%s\' is not managed.') % self.env.context.get('active_model'))

        return values

    
    def mass_subscribe(self):
        for wizard in self:
            if wizard.move_ids:
                wizard.move_ids.message_subscribe(partner_ids=wizard.partner_ids.ids)
            elif wizard.purchase_ids:
                wizard.purchase_ids.message_subscribe(partner_ids=wizard.partner_ids.ids)
            if wizard.element_ids:
                wizard.element_ids.message_subscribe(partner_ids=wizard.partner_ids.ids)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
