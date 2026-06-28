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
        string='Appointment Reference',
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
        domain=[('job_title', 'ilike', 'doctor')],
        tracking=True,
    )
    appointment_date = fields.Datetime(
        string='Appointment Date',
        required=True,
        tracking=True,
        default=fields.Datetime.now,
    )
    appointment_type = fields.Selection([
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('lab_only', 'Lab Only'),
        ('emergency', 'Emergency'),
    ], string='Type', default='consultation', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)
    chief_complaint = fields.Text(string='Chief Complaint')
    notes = fields.Text(string='Notes')
    consultation_id = fields.Many2one(
        'medical.consultation',
        string='Consultation',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

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

    # ── Constraints ───────────────────────────────────────────────────────────
    @api.constrains('appointment_date')
    def _check_appointment_date(self):
        for rec in self:
            if rec.appointment_date and rec.appointment_date.date() < fields.Date.today():
                if rec.state == 'draft':
                    pass  # allow backdating for walk-ins