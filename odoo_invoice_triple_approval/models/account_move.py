# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    custom_is_second_level_approval = fields.Boolean(
        string="Second Level Approved?",
        readonly=True,
        copy=False
    )
    custom_approval_type = fields.Selection(
        [
        ('no_approval', 'No Approval'),
        ('second_level_approval', 'Second Level Approval'),
        ('both', 'Second and Third Level Approval')
        ],
        string='Approval Type', 
        related='journal_id.custom_approval_type'
    )
    custom_is_second_level_approver_id = fields.Many2one(
        'res.users',
        string='Second Approved by', 
        readonly=True, 
        copy=False,
    )
    custom_is_third_level_approver_id = fields.Many2one(
        'res.users', 
        string='Third Approved by', 
        readonly=True, 
        copy=False,
    )
    custom_refuse_id = fields.Many2one(
        'res.users', 
        string='Refused by', 
        readonly=True, 
        copy=False,
    )
    custom_is_third_level_approval = fields.Boolean(
        string="Third Level Approved?",
        readonly=True,
        copy=False
    )
    is_custom_approval = fields.Boolean(
        string="Is Custom Approval?",
        compute="_compute_is_custom_approval",
        store = True,
        copy=False,
    )
    custom_second_level_approval_date = fields.Datetime(
        "Second Approved Date", 
        readonly=True, 
        copy=False,
        required=False,
    )
    custom_third_level_approval_date = fields.Datetime(
        "Third Approved Date", 
        readonly=True, 
        copy=False,
        required=False,
    )
    custom_reason_refuse = fields.Text(
        string='Reason for Refuse',
        required=False,
        copy=False,
        readonly=True, 
    )
    custom_refused_date = fields.Datetime(
        "Refused Date", 
        readonly=True, 
        copy=False,
        required=False,
    )
    is_custom_refuse = fields.Boolean(
        string="Is Custom Refuse?",
        compute="_compute_is_custom_refuse",
        store = True,
        copy=False,
    )
    is_custom_send_mail = fields.Boolean(
        string="Is Custom Send Mail?",
        store = True,
        readonly=True, 
        copy=False,
    )
    custom_second_approval_notify_id = fields.Many2one(
        'res.users',
        string='Second Approval Notify', 
        copy=False,
        readonly=True, 
    )
    custom_third_approval_notify_id = fields.Many2one(
        'res.users',
        string='Third Approval Notify', 
        copy=False,
        readonly=True, 
    )
    custom_is_reason_refuse = fields.Boolean(
        string="Is Reason Refuse?",
        store = True,
        readonly=True, 
        copy=False,
    )
    custom_is_refuse_ribbon = fields.Boolean(
        string="Is Refuse Ribbon?",
        copy=False,
    )
    

    @api.depends('custom_approval_type','custom_reason_refuse','is_custom_refuse')
    def _compute_is_custom_refuse(self):
        for rec in self:
            if rec.custom_approval_type == 'second_level_approval' and rec.custom_reason_refuse:
                rec.is_custom_refuse = True
                rec.is_custom_approval = True
            elif rec.custom_approval_type == 'both' and rec.custom_reason_refuse:
                rec.is_custom_refuse = True
                rec.is_custom_approval = True
            elif rec.custom_approval_type == 'no_approval' and rec.state == 'draft':
                rec.is_custom_refuse = True
                rec.is_custom_approval = True
            else:
                rec.is_custom_refuse = False
                rec.is_custom_approval = False

    @api.depends('custom_approval_type', 'custom_is_second_level_approval','custom_is_third_level_approval','is_custom_approval')
    def _compute_is_custom_approval(self):
        for rec in self:
            if rec.custom_approval_type == 'second_level_approval' and rec.custom_is_second_level_approval:
                rec.custom_is_second_level_approval = True
                rec.is_custom_approval = True
            elif rec.custom_approval_type == 'both' and rec.custom_is_second_level_approval and rec.custom_is_third_level_approval:
                rec.custom_is_second_level_approval = True
                rec.custom_is_third_level_approval = True
                rec.is_custom_approval = True
                rec.is_custom_refuse = True
            elif rec.custom_approval_type == 'no_approval' and rec.state == 'draft':
                rec.is_custom_refuse = True
                rec.is_custom_approval = True
            else:
                rec.is_custom_refuse = False
                rec.is_custom_approval = False

    def action_custom_third_level_approval(self):
        state_list = {
            'entry': 'Journal Entry',
            'out_invoice': 'Customer Invoice',
            'out_refund': 'Customer Credit Note',
            'in_invoice': 'Vendor Bill',
            'in_refund': 'Vendor Credit Note',
            'out_receipt': 'Sales Receipt',
            'in_receipt': 'Purchase Receipt',
        }
        for rec in self:
            if rec.custom_approval_type == 'both' and self.env.uid not in rec.journal_id.custom_third_approver_ids.ids:
                raise UserError(_('You are not allowed to approve.'))
            ctx = self._context.copy()
            state_list = dict(state_list) 
            ctx.update({
                'state_list': state_list.get(rec.move_type)
            })
            if rec.custom_approval_type == 'both':
                rec.write({
                    'custom_is_third_level_approval': True,
                    'custom_is_third_level_approver_id': self.env.uid,
                    'custom_third_level_approval_date': datetime.datetime.now(),
                })
            if rec.move_type == 'out_invoice' or rec.move_type == 'out_refund': 
                template = self.env.ref('odoo_invoice_triple_approval.email_template_final_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(rec.id)
                rec.write({
                    'is_custom_send_mail':True
                    })
            if rec.move_type == 'entry':
                template = self.env.ref('odoo_invoice_triple_approval.journal_entry_email_template_final_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(rec.id)
                rec.write({
                    'is_custom_send_mail':True
                    })
            if rec.move_type == 'in_invoice' or rec.move_type == 'in_refund':
                template = self.env.ref('odoo_invoice_triple_approval.vendor_bill_email_template_final_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(rec.id)
                rec.write({
                    'is_custom_send_mail':True
                    })
            if rec.move_type == 'out_receipt':
                template = self.env.ref('odoo_invoice_triple_approval.sales_receipt_email_template_final_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(rec.id)
                rec.write({
                    'is_custom_send_mail':True
                    })
            if rec.move_type == 'in_receipt':
                template = self.env.ref('odoo_invoice_triple_approval.purchase_receipt_email_template_final_approval_custom_probc')
                template.sudo().with_context(ctx).send_mail(rec.id)
                rec.write({
                    'is_custom_send_mail':True
                    })
        return True

    def button_draft(self):
        for rec in self:
            if rec.custom_approval_type == 'second_level_approval':
                rec.custom_is_second_level_approval = False
                rec.is_custom_approval = False
                rec.is_custom_refuse = False
                rec.is_custom_send_mail = False
                rec.write({
                    'custom_is_second_level_approver_id': False,
                    'custom_second_level_approval_date': False,
                    'custom_second_approval_notify_id': False,
                    })
            elif rec.custom_approval_type == 'both':
                rec.custom_is_second_level_approval = False
                rec.custom_is_third_level_approval = False
                rec.is_custom_approval = False
                rec.is_custom_refuse = False
                rec.is_custom_send_mail = False
                rec.write({
                    'custom_is_second_level_approver_id': False,
                    'custom_second_level_approval_date': False,
                    'custom_is_third_level_approver_id': False,
                    'custom_third_level_approval_date': False,
                    'custom_second_approval_notify_id': False,
                    'custom_third_approval_notify_id': False,
                    })
        return super(AccountMove,self).button_draft()

    def button_cancel(self):
        for rec in self:
            if rec.custom_approval_type == 'second_level_approval':
                rec.custom_is_second_level_approval = True
                rec.is_custom_approval = True
                rec.is_custom_refuse = True
                rec.is_custom_send_mail = True
                rec.custom_is_refuse_ribbon = False
                rec.write({
                    'custom_is_second_level_approver_id': False,
                    'custom_second_level_approval_date': False,
                    'custom_second_approval_notify_id': False,
                    })
            elif rec.custom_approval_type == 'both':
                rec.custom_is_second_level_approval = True
                rec.custom_is_third_level_approval = True
                rec.is_custom_approval = True
                rec.is_custom_refuse = True
                rec.is_custom_send_mail = True
                rec.custom_is_refuse_ribbon = False
                rec.write({
                    'custom_is_second_level_approver_id': False,
                    'custom_second_level_approval_date': False,
                    'custom_is_third_level_approver_id': False,
                    'custom_third_level_approval_date': False,
                    'custom_second_approval_notify_id': False,
                    'custom_third_approval_notify_id': False,
                    })
        return super(AccountMove,self).button_cancel()