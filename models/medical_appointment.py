# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MedicalAppointment(models.Model):
    _name = 'medical.appointment'
    _description = 'Medical Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'appointment_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='رقم المقابلة/Appointment Reference',
        required=True,
        copy=False,
        readonly=True,
        default='/',
        index=True,
    )
    patient_id = fields.Many2one(
        'res.partner',
        string='المريض|Patient',
        required=True,
        domain=[('is_patient', '=', True)],
        tracking=True,
        index=True,
    )
    doctor_id = fields.Many2one(
        'hr.employee',
        string='الدكتور|Doctor',
        required=True,
        domain=[('job_title', 'ilike', 'doctor')],
        tracking=True,
    )
    appointment_date = fields.Datetime(
        string='موعد المقابلة|Appointment Date',
        required=True,
        tracking=True,
        default=fields.Datetime.now,
    )
    appointment_type = fields.Selection([
        ('consultation', 'إستشارة/Consultation'),
        ('follow_up', 'متابعة/Follow-up'),
        ('lab_only', 'مفحص/Lab Only'),
        ('emergency', 'طوارئ/Emergency'),
    ], string='Type', default='consultation', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'جدولت/Scheduled'),
        ('confirmed', 'مؤكد/Confirmed'),
        ('in_progress', 'جاري/In Progress'),
        ('done', 'اكتمل/Done'),
        ('cancelled', 'ملغي/Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)
    chief_complaint = fields.Text(string='شكوى|Chief Complaint')
    notes = fields.Text(string='ملاحظات|Notes')
    consultation_id = fields.Many2one(
        'medical.consultation',
        string='إستشارة|Consultation',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    lab_request_ids = fields.One2many(
        'medical.lab.request', 'appointment_id', string='طلبات فحص|Lab Requests'
    )
    lab_request_count = fields.Integer(
        string='طلبات فحص|L|Lab Requests', compute='_compute_lab_request_count'
    )
    invoice_id = fields.Many2one('account.move', string='فاتورة|Invoice', readonly=True)

    @api.depends('lab_request_ids')
    def _compute_lab_request_count(self):
        for rec in self:
            rec.lab_request_count = len(rec.lab_request_ids)

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'medical.appointment'
                ) or '/'
        return super().create(vals_list)

    # ── Workflow ──────────────────────────────────────────────────────────────
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_create_consultation(self):
        self.ensure_one()
        if self.consultation_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'medical.consultation',
                'res_id': self.consultation_id.id,
                'view_mode': 'form',
            }
        consultation = self.env['medical.consultation'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'appointment_id': self.id,
            'consultation_date': self.appointment_date,
        })
        self.consultation_id = consultation.id
        self.state = 'in_progress'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'medical.consultation',
            'res_id': consultation.id,
            'view_mode': 'form',
        }
    
    def action_create_lab_request(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Lab Request',
            'res_model': 'medical.lab.request',
            'view_mode': 'form',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_appointment_id': self.id,
            },
        }

    # ── Constraints ───────────────────────────────────────────────────────────
    @api.constrains('appointment_date')
    def _check_appointment_date(self):
        for rec in self:
            if rec.appointment_date and rec.appointment_date.date() < fields.Date.today():
                if rec.state == 'draft':
                    pass  # allow backdating for walk-ins

    def action_create_invoice(self):
        """Create invoice from appointment + all linked lab requests."""
        self.ensure_one()
        lines = []
        # Add lab request products
        for req in self.lab_request_ids:
            for tmpl in req.template_ids:
                if tmpl.product_id:
                    lines.append((0, 0, {
                        'product_id': tmpl.product_id.id,
                        'quantity': 1,
                        'price_unit': tmpl.product_id.lst_price,
                        'name': tmpl.name,
                    }))
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.patient_id.id,
            'invoice_line_ids': lines,
        })
        self.invoice_id = invoice.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    def action_view_lab_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Requests',
            'res_model': 'medical.lab.request',
            'view_mode': 'list,form',
            'domain': [('appointment_id', '=', self.id)],
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_appointment_id': self.id,
            },
        }

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Requests',
            'res_model': 'account_move',
            'view_mode': 'list,form',
            'domain': [('move_id', '=', self.invoice_id.id)],
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_appointment_id': self.id,
            },
        }