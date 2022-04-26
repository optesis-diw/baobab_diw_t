# -*- coding: utf-8 -*-

import datetime 

from odoo import models, fields , _
from odoo.exceptions import UserError


class AccountMoveRefuseWizard(models.TransientModel):
    _name = 'custom.account.move.refuse.wizard'
    _description = 'custom.account.move.refuse.wizard'

    custom_reason = fields.Text(
        string='Reason for Refuse',
        required=True,
        copy=True,
    )

    def custom_reset_to_draft(self):
        move_id = self.env['account.move'
            ].browse(self._context.get('active_ids'))
        if move_id.custom_approval_type == 'second_level_approval':
            move_id.custom_is_second_level_approval = False
            move_id.is_custom_approval = False
            move_id.is_custom_refuse = False
            move_id.is_custom_send_mail = False
            move_id.write({
                'custom_is_second_level_approver_id': False,
                'custom_second_level_approval_date': False,
                'custom_second_approval_notify_id': False,
                })
        elif move_id.custom_approval_type == 'both':
            move_id.custom_is_second_level_approval = False
            move_id.custom_is_third_level_approval = False
            move_id.is_custom_approval = False
            move_id.is_custom_refuse = False
            move_id.is_custom_send_mail = False
            move_id.write({
                'custom_is_second_level_approver_id': False,
                'custom_second_level_approval_date': False,
                'custom_is_third_level_approver_id': False,
                'custom_third_level_approval_date': False,
                'custom_second_approval_notify_id': False,
                'custom_third_approval_notify_id': False,
                })
        return True

    def action_refuse_approval(self):
        move_id = self.env['account.move'
            ].browse(self._context.get('active_ids'))
        if move_id.custom_approval_type in ['second_level_approval'] and self.env.uid not in move_id.journal_id.custom_second_approver_ids.ids:
            raise UserError(_('You are not allowed to refuse.'))
        if move_id.custom_approval_type in ['second_level_approval','both'] and self.env.uid not in move_id.journal_id.custom_second_approver_ids.ids and self.env.uid not in move_id.journal_id.custom_third_approver_ids.ids:
            raise UserError(_('You are not allowed to refuse.'))
        move_id.write({
            'custom_reason_refuse' : self.custom_reason,
            'custom_refuse_id': self.env.uid,
            'custom_refused_date': datetime.datetime.now(),
            'custom_is_reason_refuse' : True,
            'custom_is_refuse_ribbon' : True
                })
        group_msg = _('Your Entry has been Refused')
        move_id.sudo().message_post(body=group_msg,message_type='comment')
        self.custom_reset_to_draft()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
