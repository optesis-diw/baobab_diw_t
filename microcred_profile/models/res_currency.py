# -*- coding: utf-8 -*-
# Copyright 2017 SYLEAM Info Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class res_currency(models.Model):
    _inherit = "res.currency"

    update = fields.Boolean(string='Update', default=True)
