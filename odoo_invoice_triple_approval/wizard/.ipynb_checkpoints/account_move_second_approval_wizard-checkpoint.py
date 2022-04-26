# -*- coding: utf-8 -*-

from odoo import models, fields , api , _
from odoo.exceptions import UserError


class AccountMoveSecondApprovalNotifyWizard(models.TransientModel):
    _name = 'custom.account.move.second.approval.wizard'
    _description = 'custom.account.move.second.approval.wizard'

    custom_second_approval_notify_id = fields.Many2one(
        'res.users',
        string='Second Approval Responsible', 
        copy=False,
        required=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string="Move",
        readonly=True
    )

    @api.model
    def default_get(self, default_fields):
        res = super(AccountMoveSecondApprovalNotifyWizard,self).default_get(default_fields)
        res['move_id'] = self.env['account.move'].browse(int(self._context.get('active_id'))).id
        return res

    @api.onchange('move_id')
    def onchange_move_id(self):
        domain = {}
        if self.move_id:
            domain = {'custom_second_approval_notify_id': [('id', 'in', self.move_id.journal_id.custom_second_approver_ids.ids)]}
        return {'domain': domain}

    def action_account_move_second_approval_notify(self):
        move_id = self.env['account.move'
            ].browse(self._context.get('active_ids'))
        ctx = self._context.copy()
        state_list = {
            'entry': 'Journal Entry',
            'out_invoice': 'Customer Invoice',
            'out_refund': 'Customer Credit Note',
            'in_invoice': 'Vendor Bill',
            'in_refund': 'Vendor Credit Note',
            'out_receipt': 'Sales Receipt',
            'in_receipt': 'Purchase Receipt',
        }
        state_list = dict(state_list) 
        ctx.update({
            'state_list': state_list.get(move_id.move_type)
        })
        if move_id.custom_approval_type == 'second_level_approval' or move_id.custom_approval_type == 'both':
            move_id.write({
                'custom_second_approval_notify_id' : self.custom_second_approval_notify_id,
                'custom_is_refuse_ribbon' : False
                })
            if move_id.move_type == 'out_invoice' or move_id.move_type == 'out_refund': 
                template = self.env.ref('odoo_invoice_triple_approval.email_template_second_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(move_id.id)
                move_id.write({
                    'is_custom_send_mail':True
                    })
            if move_id.move_type == 'entry':
                template = self.env.ref('odoo_invoice_triple_approval.journal_entry_email_template_second_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(move_id.id)
                move_id.write({
                    'is_custom_send_mail':True
                    })
            if move_id.move_type == 'in_invoice' or move_id.move_type == 'in_refund':
                template = self.env.ref('odoo_invoice_triple_approval.vendor_bill_email_template_second_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(move_id.id)
                move_id.write({
                    'is_custom_send_mail':True
                    })
            if move_id.move_type == 'out_receipt':
                template = self.env.ref('odoo_invoice_triple_approval.sales_receipt_email_template_second_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(move_id.id)
                move_id.write({
                    'is_custom_send_mail':True
                    })
            if move_id.move_type == 'in_receipt':
                template = self.env.ref('odoo_invoice_triple_approval.purchase_receipt_email_template_second_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(move_id.id)
                move_id.write({
                    'is_custom_send_mail':True
                    })
        return True
