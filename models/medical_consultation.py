# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MedicalConsultation(models.Model):
    _name = 'medical.consultation'
    _description = 'Medical Consultation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'consultation_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Consultation Reference',
        required=True,
        copy=False,
        readonly=True,
        default='/',
        index=True,
    )
    patient_id = fields.Many2one(
        'res.partner',
        string='Patient',
        required=True,
        domain=[('is_patient', '=', True)],
        tracking=True,
        index=True,
    )
    doctor_id = fields.Many2one(
        'hr.employee',
        string='Doctor',
        required=True,
        tracking=True,
    )
    appointment_id = fields.Many2one(
        'medical.appointment',
        string='Appointment',
        tracking=True,
    )
    consultation_date = fields.Datetime(
        string='Consultation Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)
    # ── Clinical ──────────────────────────────────────────────────────────────
    chief_complaint = fields.Text(string='Chief Complaint')
    diagnosis = fields.Text(string='Diagnosis', tracking=True)
    clinical_notes = fields.Text(string='Clinical Notes')
    prescription = fields.Text(string='Prescription')
    follow_up_date = fields.Date(string='Follow-up Date')
    follow_up_notes = fields.Text(string='Follow-up Notes')
    # ── Lab Requests ──────────────────────────────────────────────────────────
    lab_request_ids = fields.One2many(
        'medical.lab.request',
        'consultation_id',
        string='Lab Requests',
    )
    lab_request_count = fields.Integer(
        string='Lab Requests',
        compute='_compute_lab_request_count',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)


    # ── Compute ───────────────────────────────────────────────────────────────
    def _compute_lab_request_count(self):
        for rec in self:
            rec.lab_request_count = len(rec.lab_request_ids)

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'medical.consultation'
                ) or '/'
        return super().create(vals_list)

    # ── Workflow ──────────────────────────────────────────────────────────────
    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            if rec.appointment_id:
                rec.appointment_id.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_create_lab_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Lab Request',
            'res_model': 'medical.lab.request',
            'view_mode': 'form',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_id.id,
                'default_consultation_id': self.id,
            },
        }

    # def action_create_invoice(self):
    #     self.ensure_one()
    #     product = self.env['product.product'].search([('default_code','=','CONSULT1')])
    #     if product:
    #         lines = []
    #         Invoice = self.env['account.move']
    #         for rec in self:
            
    #             rec.invoice_id = Invoice.create({
    #                 'move_type' :'out_invoice',
    #                 'partner_id':rec.patient_id.id,
    #                 'line_ids'  :
    #                 (0, 0, {
    #                     'product_id':  product.id,
    #                     'quantity':    1,
    #                     'price_unit':  product.lst_price,
    #                     'name':        product.name,
    #             }),
    #         })
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Create Invoice',
    #         'res_model': 'account.move',
    #         'view_mode': 'form',
    #         'context': {
    #             'default_partner_id'  : rec.patient_id.id,
    #             'default_move_type'   : 'out_invoice',
    #             'default_default_code': 'CONSULT1',
    #             'default_invoice_id'  : rec.invoice_id,
    #         },
    #     }
    from odoo import Command

    def action_create_invoice(self):
        self.ensure_one()
        
        # Locate the consultation product
        product = self.env['product.product'].search([('default_code', '=', 'CONSULT1')], limit=1)
        if not product:
            return  # Or raise an UserError warning that the product is missing
            
        Invoice = self.env['account.move']
        
        # Build the invoice record
        invoice = Invoice.create({
            'move_type': 'out_invoice',
            'partner_id': self.patient_id.id,
            # invoice_line_ids is safer for customer invoices than raw line_ids
            'invoice_line_ids': [
                self.Command.create({
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': product.lst_price,
                    'name': product.name,
                })
            ],
        })
        
        # Link the newly created invoice back to this consultation record
        self.invoice_id = invoice.id

        # Return a window action to open the freshly made draft invoice view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id, # Opens the exact record instead of a blank form
            'context': {
                'default_move_type': 'out_invoice',
            },
        }
