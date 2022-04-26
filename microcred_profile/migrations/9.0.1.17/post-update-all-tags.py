# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2017 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Chris TRIBBECK <chris.tribbeck@syleam.fr>
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

from odoo import SUPERUSER_ID, api
import logging
logger = logging.getLogger('Update tags (transform to all tags)')


def migrate(cr, v):
    data_to_update = [
        # 'BE',  # Budget Element
        # 'AI',  # Invoice
        # 'AIL',  # Invoice Line
        # 'POL',  # Purchase Order Line
        # 'AML',  # Journal item
        # 'AADL',  # Asset depreciation line
        # 'AAL',  # Analytical item
        # 'BLT',  # Budget Line Type
        # Note : Purchase Orders, Product Templates and Product Categories are not managed because they were not used (no data to migrate)
    ]
    # TODO : Set to True to execute all upgrades (essential for delivery)
    do_all = True
    with api.Environment.manage():
        uid = SUPERUSER_ID
        ctx = api.Environment(cr, uid, {})['res.users'].context_get()
        env = api.Environment(cr, uid, ctx)
        companies = env['res.company'].search([])
        for company in companies:
            print("Company", company.name)
            tag_transco = {}
            if company.id == 1:
                tags = env['budget.element.tag'].search([])
                axis_types = {
                    'programme': env.ref('microcred_profile.axis_sas_programme'),
                    'finance': env.ref('microcred_profile.axis_sas_finance'),
                    'other': env.ref('microcred_profile.axis_sas_other')
                }
                for tag in tags:
                    new_tag = env['account.axis.tag'].create({
                        'axis_id': axis_types[tag.type].id,
                        'name': tag.name,
                        'color': tag.color,
                    })
                    tag_transco[tag] = new_tag
            else:
                for axis in env['account.axis'].search([('company_id', '=', 1), ('number', '<=', 4)]):
                    if not env['account.axis'].search([('company_id', '=', company.id), ('number', '=', axis.number)]):
                        axis.copy(default={
                            'company_id': company.id,
                        })

            axis_transco = {}
            if 'BE' in data_to_update or do_all:
                elements = env['budget.element'].search([('company_id', '=', company.id)])
                for element in elements:
                    new_tags = []
                    if company.id == 1:
                        for tag in element.tag_ids:
                            new_tags.append(tag_transco[tag])
                        for tag in element.programme_tag_ids:
                            new_tags.append(tag_transco[tag])
                        for tag in element.finance_tag_ids:
                            new_tags.append(tag_transco[tag])

                    for tag in element.axis_tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup,
                                    'company_id': company.id
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('BE:', element.id)
                    element.write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })

            if 'POL' in data_to_update or do_all:
                purchase_lines = env['purchase.order.line'].search([('tag_ids', '!=', False), ('order_id.company_id', '=', company.id)])
                for line in purchase_lines:
                    new_tags = []
                    for tag in line.tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('POL:', line.id)
                    line.with_context({'no_asset_check': True}).write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })

            if 'POL' in data_to_update or do_all:
                purchases = env['purchase.order'].search([('company_id', '=', company.id)])
                purchases.set_axis_fields()

            if 'AIL' in data_to_update or do_all:
                invoice_lines = env['account.move.line'].search([('tag_ids', '!=', False), ('move_id.company_id', '=', company.id)])
                for line in invoice_lines:
                    new_tags = []
                    for tag in line.tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('AIL:', line.id)
                    line.with_context({'no_asset_check': True}).write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })

            if 'AI' in data_to_update or do_all:
                invoices = env['account.move'].search([('tag_ids', '!=', False), ('company_id', '=', company.id)])
                for line in invoices:
                    new_tags = []
                    for tag in line.tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('AI:', line.id)
                    line.with_context({'no_asset_check': True}).write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })
                    line.set_axis_fields()

                invoices = env['account.move'].search([('company_id', '=', company.id)])
                invoices.set_axis_fields()

            if 'AML' in data_to_update or do_all:
                move_lines = env['account.move.line'].search([('tag_ids', '!=', False), ('move_id.company_id', '=', company.id)])
                for line in move_lines:
                    new_tags = []
                    for tag in line.tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('AML:', line.id)
                    line.with_context({'no_asset_check': True}).write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })

            if 'AADL' in data_to_update or do_all:
                depreciation_lines = env['account.asset'].search([('tag_ids', '!=', False), ('asset_id.company_id', '=', company.id)])
                for line in depreciation_lines:
                    new_tags = []
                    for tag in line.tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('AADL:', line.id)
                    line.with_context({'no_asset_check': True}).write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })

            if 'AAL' in data_to_update or do_all:
                analytic_lines = env['account.analytic.line'].search([('tag_ids', '!=', False), ('company_id', '=', company.id)])
                for line in analytic_lines:
                    new_tags = []
                    for tag in line.tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('AAL:', line.id)
                    line.with_context({'no_asset_check': True}).write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })

            if 'BTL' in data_to_update or do_all:
                budget_line_types = env['budget.line.type'].search([('tag_ids', '!=', False), ('company_id', '=', company.id)])
                for line in budget_line_types:
                    new_tags = []
                    for tag in line.tag_ids:
                        if tag in axis_transco:
                            new_tags.append(axis_transco[tag])
                        else:
                            domain = [
                                ('name', '=', tag.name),
                                ('axis_id.number', '=', int(tag.axis[0])),
                                ('axis_id.company_id', '=', company.id)
                            ]
                            subgroup = ''
                            if tag.axis[0] == '4':
                                subgroup = tag.axis[1]
                                domain.append(('subgroup', '=', subgroup))
                            axis_tag = env['account.axis.tag'].search(domain)
                            if not axis_tag:
                                axis_tag = env['account.axis.tag'].create({
                                    'name': tag.name,
                                    'axis_id': env['account.axis'].search([('number', '=', tag.axis[0]), ('company_id', '=', company.id)]).id,
                                    'subgroup': subgroup
                                })
                            axis_transco[tag] = axis_tag
                            new_tags.append(axis_tag)

                    print('BLT:', line.id)
                    line.with_context({'no_asset_check': True}).write({
                        'all_tag_ids': [(6, 0, [r.id for r in new_tags])]
                    })

    print("All finished !")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
