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

from odoo import models, api, fields
from collections import defaultdict


class AccountAxisTagWrapper(models.Model):
    _name = 'account.axis.tag.wrapper'
    _description = 'Account Axis Tag Wrapper'

    """
    This class is used via inheritance to other classes (budget.element, purchase.order, ...)
    so as to factorise the individual axis field handling code
    """

    all_tag_ids = fields.Many2many(comodel_name='account.axis.tag', string=' axis Tags2', help='Select the tags.')

    axis_1 = fields.Char(string='Axis 1', size=64, readonly=True, index=True)
    axis_2 = fields.Char(string='Axis 2', size=64, readonly=True, index=True)
    axis_3 = fields.Char(string='Axis 3', size=64, readonly=True, index=True)
    axis_4 = fields.Char(string='Axis 4', size=64, readonly=True, index=True)
    axis_5 = fields.Char(string='Axis 5', size=64, readonly=True, index=True)
    axis_6 = fields.Char(string='Axis 6', size=64, readonly=True, index=True)
    axis_7 = fields.Char(string='Axis 7', size=64, readonly=True, index=True)
    axis_8 = fields.Char(string='Axis 8', size=64, readonly=True, index=True)

    
    def set_axis_fields(self):
        AccountAxisTag = self.env['account.axis.tag']
        (axis_fields, has_child) = self.get_axis_fieldnames()

        for record in self:
            tags = defaultdict(list)
            # Get the tags
            these_tags = record.all_tag_ids
            if has_child:
                these_tags = record.child_tag_ids

            for tag in these_tags:
                tags[tag.axis_id].append(tag.id)

            axes = axis_fields.copy()

            # Reorder the tags alphabetically
            for axis in tags:
                if 'axis_%d' % axis.number in axis_fields or 'x_axis_%d' % axis.number in axis_fields:
                    if len(tags[axis]) > 1:
                        tag_names = ', '.join(AccountAxisTag.search([('id', 'in', tags[axis])], order='name').mapped('name'))
                    elif tags[axis]:
                        tag_names = AccountAxisTag.browse(tags[axis]).name

                    if tag_names:
                        if 'axis_%d' % axis.number in axis_fields:
                            axes['axis_%d' % axis.number] = tag_names
                        else:
                            axes['x_axis_%d' % axis.number] = tag_names

            record.write(axes)

    @api.model
    def get_axis_fieldnames(self):
        fields = self.fields_get_keys()
        axis_fields = {}
        has_child = False
        for field in fields:
            number = False
            if field[:5] == 'axis_':
                number = field[5:]
            elif field[:7] == 'x_axis_':
                number = field[7:]
            elif field == 'child_tag_ids':
                has_child = True

            if number and number.isdigit():
                axis_fields[field] = False

        return(axis_fields, has_child)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
