# -*- coding: utf-8 -*-
##############################################################################
#
#    microcred_profile module for odoo, Profile for Microcred
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
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

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin', 'account.payment']
    _name = 'account.payment'
    #manage form view draft not new
    state = fields.Selection(
        [('draft', 'Nouveau'),
         ('fonctional', 'Fonctionnel'),
         ('on_repair', 'En Réparation'),
         ('declassed', 'Déclassé')],
        'Etat', default="draft")

#     @api.onchange('partner_type')
#     def _onchange_partner_type(self):
#         # Set partner_id domain
#         ret = super(AccountPayment, self)._onchange_partner_type()
#         if ret.get('domain').get('partner_id'):
#             ret['domain']['partner_id'].append(('user_can_view', '=', True))
#         return ret

    
#     def post(self):
#         """
#         This sets the state of invoices to 'open' if they are 'to pay' because the payment requires them to be in an open state.
#         """
#         invoices = self.mapped('move_ids')
#         if any(inv.state != 'to pay' for inv in invoices.filtered(lambda r: r.type in ('in_invoice', 'in_refund'))):
#             raise ValidationError(_("The payment cannot be processed because the invoice is not to be paid!"))
#         if any(inv.state != 'open' for inv in invoices.filtered(lambda r: r.type in ('out_invoice', 'out_refund'))):
#             raise ValidationError(_("The payment cannot be processed because the invoice is not to be paid!"))
#         invoices.filtered(lambda r: r.state == 'to pay').with_context({'no_microcred_state_change': 'to pay'}).write({'state': 'open'})
#         bad_partners = self.mapped('move_ids.partner_id').filtered(lambda r: r.thirdparty_account is False).mapped('name')
#         if bad_partners:
#             raise ValidationError(_("The following partner(s) do not have a third-party account: %s") % ','.join(bad_partners))

#         ret = super(AccountPayment, self).post()

#         for payment in self:
#             payment.move_line_ids.write({'name': _('PAYMENT:') + ' ' + ', '.join(payment.mapped('move_ids.partner_id.thirdparty_account')).upper() + ' - ' + (payment.communication or '')})

#         invoices = self.mapped('move_ids').filtered(lambda r: r.state == 'open' and r.type in ('in_invoice', 'in_refund'))
#         if invoices:
#             invoices.with_context({'no_microcred_state_change': 'to pay'}).write({'state': 'to pay'})

#         return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
