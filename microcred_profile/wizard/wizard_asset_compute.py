# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger('microcred_profile')


class AssetDepreciationConfirmationWizard(models.TransientModel):
    _inherit = "account.asset"

    company_id = fields.Many2one(comodel_name='res.company', string='Company', help='Select the company')

    @api.model
    def default_get(self, fields_list):
        """
        Get the invoice(s)/purchase order(s) or budget element(s)
        """

        values = super(AssetDepreciationConfirmationWizard, self).default_get(fields_list)

        values['company_id'] = self.env.user.company_id.id

        return values

    
    def asset_compute(self):
        self.ensure_one()
        _logger.info('>>>>>>>>>>>>>>> Started computing')
        context = self._context
        domain = [('state', '=', 'open'), ('category_id.type', '=', context.get('asset_type'))]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        assets = self.env['account.asset'].search(domain)
        created_move_ids = assets.with_context({'do_not_calculate_budgets': True})._compute_entries(self.date)
        _logger.info('>>>>>>>>>>>>>>> Ended computing')
        if created_move_ids:
            self._cr.execute("SELECT DISTINCT(budget_element_id) FROM account_move_line WHERE move_id IN %s AND budget_element_id IS NOT null", [tuple(created_move_ids)])
            data = self._cr.fetchall()
            element_ids = [x[0] for x in data]
            self.env['budget.element'].browse(element_ids).calculate_amounts()
        _logger.info('>>>>>>>>>>>>>>> Ended calculating')
        if context.get('asset_type') == 'purchase':
            title = _('Created Asset Moves')
        else:
            title = _('Created Revenue Moves')
        return {
            'name': title,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(map(str, created_move_ids)) + "])]",
            'type': 'ir.actions.act_window',
        }
