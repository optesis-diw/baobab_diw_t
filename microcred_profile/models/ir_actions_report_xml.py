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

from odoo import models, api, fields, _


class IrActionswebXml(models.Model):
    _inherit = 'ir.actions.report'

    flag_printing = fields.Boolean(string='Flag printing', help='If checked, the printing of this web will be logged.')

    
    def flag_web_print(self, record_ids):
        self.ensure_one()
        records = self.env[self.model].browse(record_ids)
        if hasattr(records, 'message_post'):
            records.message_post(body=_('Document printed.'))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
