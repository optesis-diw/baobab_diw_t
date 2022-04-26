# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.Syleam.fr/>)
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

{
    'name': 'Microcred Profile',
    'version': '1.0.1',
    'category': 'Custom',
    'description': """Profile for Microcred""",
    'author': 'SYLEAM updated by Moore Senegal',
    'website': 'https://www.moore.sn/',
    'depends': [
        'mail',
        'base',
        'advanced_budget',
        'analytic',
        'account',
        'account_asset',
        #'account_online_sync',
        'web',
        #'portal_sale',
        'sale',
        'purchase',
        # 'st_dynamic_list',
        #'web_export_view',
        # 'account_extra_web_partnerledger',
        # 'account_web_partnerbalance',
    ],
    'images': [],
    'data': [
#         'data/base.xml',
#         'data/analytic_tags.xml',
#         'data/budget_element_types.xml',
#         'data/res_company.xml',
#         'data/ir_module_category.xml',
#         'data/ir_sequence.xml',
        #'data/web_paperformat.xml',
          'data/mail_template.xml',
#         'data/budget_element_subtypes.xml',
#         'data/account_axis.xml',
          'data/invoice_tag_update.xml',

        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        'wizard/add_budget_details.xml',
        'wizard/add_budget_distribution.xml',
        'wizard/asset_sale_date.xml',
        'wizard/change_account_tags.xml',
        'wizard/export_budget.xml',
        'wizard/modify_invoice_budget_line.xml',
        'wizard/define_monthly_budget.xml',
        'wizard/mass_subscription.xml',
        'wizard/export_sage.xml',
        'wizard/export_journal_items.xml',
        'wizard/view_budget_data.xml',
        'wizard/view_budget_element.xml',
        'wizard/reaffect_budget.xml',
        'wizard/transfer_budget_amount.xml',
        'wizard/wizard_asset_compute.xml',

        'views/menus.xml',
        'views/account_account.xml',
        'views/account_axis.xml',
        'views/res_partner.xml',
        'views/res_users.xml',
        'views/budget_element_tag.xml',
        'views/budget_reinvoice_batch.xml',
        'views/budget_line_type.xml',
        'views/account_analytic_line.xml',
        'views/account_move_line.xml',
        'views/account_move.xml',
        'views/account_analytic_tag.xml',
        'views/account_journal.xml',
        'views/account_invoice.xml',
        'views/account_journal_sage_export.xml',
        'views/res_company.xml',
        'views/product_template.xml',
        'views/project_project.xml',
        'views/budget_element.xml',
        'views/product_category.xml',
        'views/hr_employee.xml',
        'views/microcred.xml',
        'views/purchase_order.xml',
        'views/hr_import_payroll.xml',
        'views/purchase_order_line.xml',
        'views/expensify_budget.xml',
        'views/expensify_product.xml',
        'views/expensify_import.xml',
        'views/account_payment.xml',
        'views/account_bank_statement.xml',
        'views/account_asset.xml',
        #'views/ir_act_web_xml.xml',
        'views/res_currency.xml',
        #
        #'workflows/account_invoice.xml',

        #'report/header.xml',
        #'report/invoice.xml',
        #'report/footer.xml',
        'report/purchase.xml',
        # 'report/bank_statement.xml',
        #report purchase 
        'report/optesis_purchase_report_menu.xml',
        'report/optesis_purchase_budget_validated.xml',
        'report/optesis_head_validation.xml',
        
    ],
    'test': [],
    # 'external_dependancies': {'python': ['kombu'], 'bin': ['which']},
    'css': ['static/src/css/microcred.css','static/src/css/layout.css','static/src/css/invoice.css' ],
    'qweb': [
        "static/src/xml/debug.xml",
        "static/src/xml/base.xml",
    ],
    'installable': True,
    'active': False,
    'license': 'AGPL-3',



}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
