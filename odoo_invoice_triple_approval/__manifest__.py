# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.
{
    'name': 'Invoice - Vendor Bill - Journal Entry Double and Tripple Approval',
    'version': '3.2.5',
    'price': 119.0,
    'depends': [
        'account',
    ],
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Accounting/Accounting',
    'summary':  """Allow you to have double and tripple approval workflow on Invoice, Vendor Bill, Journal Entry.....""",
    'description': """
Invoice Triple Approval
invoice approval workflow
invoice approve
invoice approval
approve invoice
reject invoice
approval workflow on invoice
approval invoice
invoice document approval
manager approve invoice
invoice approve manager
Added Manager Approval 
Added Director Approval
invoice approval flow
invoice director approve
invoice manager approve
invoice accounting approve
invoice account deparement approve
invoice approval
invoice approve
invoice workflow
invoice workflow approval
User Validation For invoice
invoice limit
invoice flow
invoice management
invoice system
invoice odoo
Rejected Invoice
Reject Invoice with reason
invoice reject
reject invoice
refuse invoice
invoice refuse
Journal Entry Workflow
This app allow functionalitis for perform workflow on journal entries.
Journal Entry Need Review Approval for Audit
Journal Entry with need review, correction, approve and post workflow
journal entry approve
journal entry audit
audit journal
audit
audit journal items
journal items audit
need correction journal entry
journal entry correction
journal correct
journal entry review
review journal entry
review journal items
account audit
audit accounting
post journal entry
journal entry post
    """,
    
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'www.probuse.com',
    'images': ['static/description/image.png'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/odoo_invoice_triple_approval/903',#'https://youtu.be/svvVtqkUnss',
    'data': [
        'security/ir.model.access.csv',
        'data/invoice_email_template.xml',
        'data/journal_entry_email_template.xml',
        'data/purchase_receipt_email_template.xml',
        'data/sales_receipt_email_template.xml',
        'data/vendor_bill_email_template.xml',
        'wizard/account_move_refuse_wizard_view.xml',
        'wizard/account_move_second_approval_wizard_view.xml',
        'wizard/account_move_third_approval_wizard_view.xml',
        'views/account_journal_view.xml',
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
