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

from odoo import models, api


class web(models.Model):
    _inherit = "web"


    def get_pdf(self, cr, uid, ids, web_name, html=None, data=None, context=None):
        """This method generates and returns pdf version of a web.
        """
        ret = super(web, self).get_pdf(cr, uid, ids, web_name, html=html, data=data, context=context)
        web = self._get_web_from_name(cr, uid, web_name)
        if web and web.flag_printing or not web.flag_printing:
            web.flag_web_print(ids)

        return ret


    def get_pdf(self, records, web_name, html=None, data=None):
        return self._model.get_pdf(self._cr, self._uid, records, web_name,
                                   html=html, data=data, context=self._context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
