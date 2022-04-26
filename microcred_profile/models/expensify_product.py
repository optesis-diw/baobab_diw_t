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

from odoo import models, fields, api


class ExpensifyProduct(models.Model):
    _name = 'expensify.product'
    _description = 'Expensify product'
    _sql_constraints = [
        ('purpose_category_company_unique', 'unique (purpose, category, company_id)', 'You cannot create the more than one rule for the same purpose, category and company!'),
    ]

    purpose = fields.Char(string='Purpose', size=64, help='Enter the purpose.', required=True, index=True)
    category = fields.Char(string='Category', size=64, help='Enter the category.', required=True, index=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', help='Select a company (if there are any differences).', index=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', help='Select the product associated.', required=True)

    @api.model
    def get_product(self, purpose, category, company):
        domain_general = [('purpose', '=', purpose), ('category', '=', category)]
        if company:
            product = self.search([('company_id', '=', company.id)] + domain_general)
        if not product:
            product = self.search(domain_general)
        if product:
            return product.product_id
        return company and company.default_expensify_product_id or self.env['product.product']


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
