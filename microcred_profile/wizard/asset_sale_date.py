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


from odoo import models, api, fields, exceptions


class WizardAssetSaleDate(models.TransientModel):
    _name = 'wizard.asset.sale.date'
    _description = 'Asset sale date wizard'

    asset_id = fields.Many2one(comodel_name='account.asset', string='Asset', help='The asset to be sold.')
    account_id = fields.Many2one(comodel_name='account.account', string='Asset Sales/Disposal account',
                                 help='Select the sale/disposal account.')
    #depreciation_line_id = fields.Many2one(comodel_name='account.asset.depreciation_line', string='Depreciation', help='Select the depreciation')
    depreciation_line_id = fields.Many2one(comodel_name='account.asset', string='Depreciation', help='Select the depreciation')
    date_sold = fields.Date(string='Date sold', help='The date the asset was sold.')
    date_min = fields.Date(string='The miniumum date', help='The minimum date.')
    company_id = fields.Many2one(comodel_name='res.company', string='Company')

    @api.model
    def default_get(self, fields_list):
        """
        Return budget line information
        """

        values = super(WizardAssetSaleDate, self).default_get(fields_list)

        if self.env.context.get('active_model') == 'account.asset':
            asset = self.env['account.asset'].browse(self._context.get('active_id'))

            values['asset_id'] = asset.id
            values['account_id'] = asset.product_account_id.id
            values['company_id'] = asset.company_id.id
            last_date = False
            for line in asset.depreciation_line_ids:
                if not line.move_check and (line.depreciation_date < last_date or not last_date):
                    last_date = line.depreciation_date
                    values['depreciation_line_id'] = line.id
                    values['date_sold'] = line.depreciation_date

        return values

    
    def validate(self):
        """
        Close the asset
        """
        self.ensure_one()
        context = self.env.context.copy()
        context.update({
            'date_sold': self.date_sold,
            'product_account_id': self.account_id.id
        })
        last_date = False
        for line in self.asset_id.depreciation_line_ids:
            if line.depreciation_date <= self.date_sold and (line.depreciation_date > last_date or not last_date):
                context['budget_element_id'] = line.budget_element_id.id
                last_date = line.depreciation_date

        return self.with_context(context).asset_id.set_to_close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
