# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError



        ##############################################################################
        #
        #    
        #   
        #            Baobab 2022 8 - mICROCRED
        #             get reference de payment dans payment register by CTD
        #
        ##############################################################################

class _inherit_AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    
    # communication = fields.Char(string="Memo", store=True, readonly=False,
    #     compute='_compute_communication')
   
    #add by CTD
    @api.depends('can_edit_wizard')
    def _compute_communication(self):
        communication = super(_inherit_AccountPaymentRegister, self)._compute_communication()
        for wizard in self:
            if wizard.can_edit_wizard:
                batches = wizard._get_batches()
                wizard.communication = batches[0]['lines'].move_id.payment_reference
            else:
                wizard.communication = False
        return communication