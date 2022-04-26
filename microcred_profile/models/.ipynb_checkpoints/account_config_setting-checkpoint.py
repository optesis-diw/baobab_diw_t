# -*- coding: utf-8 -*-
# Copyright 2017 SYLEAM Info Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _update_currency_ecb(self):
        pass

    def _update_currency_yahoo(self):
        pass
