# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Medical Identity ──────────────────────────────────────────────────────
    is_patient = fields.Boolean(string='Is Patient', default=False, index=True)
    medical_number = fields.Char(
        string='Medical Number',
        copy=False,
        readonly=True,
        index=True,
    )
    # ── Demographics ──────────────────────────────────────────────────────────
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    date_of_birth = fields.Date(string='Date of Birth')
    # age = fields.Integer(
    #     string='Age',
    #     compute='_compute_age',
    #     store=False,
    # )
    age = fields.Integer(string='Age',)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
        ('o+', 'O+'), ('o-', 'O-'),
    ], string='Blood Group')
    # ── Emergency Contact ─────────────────────────────────────────────────────
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Relation')
    # ── Medical Notes ─────────────────────────────────────────────────────────
    medical_notes = fields.Text(string='Medical Notes')
    known_allergies = fields.Text(string='Known Allergies')
    chronic_conditions = fields.Text(string='Chronic Conditions')
    # ── Statistics ────────────────────────────────────────────────────────────
    appointment_count = fields.Integer(
        string='Appointments',
        compute='_compute_appointment_count',
    )
    lab_request_count = fields.Integer(
        string='Lab Requests',
        compute='_compute_lab_request_count',
    )
    invoice_count = fields.Integer(
        string='Invoices',
        compute='_compute_invoice_count',
    )

    # ── Compute Methods ───────────────────────────────────────────────────────
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                dob = rec.date_of_birth
                rec.age = (
                    today.year - dob.year
                    - ((today.month, today.day) < (dob.month, dob.day))
                )
            else:
                rec.age = 0

    def _compute_appointment_count(self):
        Appointment = self.env['medical.appointment']
        for rec in self:
            rec.appointment_count = Appointment.search_count(
                [('patient_id', '=', rec.id)]
            )

    def _compute_lab_request_count(self):
        LabRequest = self.env['medical.lab.request']
        for rec in self:
            rec.lab_request_count = LabRequest.search_count(
                [('patient_id', '=', rec.id)]
            )

    def _compute_invoice_count(self):
        Invoice = self.env['account.move']
        for rec in self:
            rec.invoice_count = Invoice.search_count([
                ('partner_id', '=', rec.id),
                ('move_type', '=', 'out_invoice'),
            ])

    # ── ORM Overrides ─────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_patient') and not vals.get('medical_number'):
                vals['medical_number'] = self.env['ir.sequence'].next_by_code(
                    'medical.patient'
                ) or '/'
        return super().create(vals_list)

    # ── Constraints ───────────────────────────────────────────────────────────
    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > date.today():
                raise ValidationError(
                    'Date of birth cannot be in the future.'
                )

    # ── Smart Button Actions ──────────────────────────────────────────────────
    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'medical.appointment',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_lab_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Requests',
            'res_model': 'medical.lab.request',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('move_type', '=', 'out_invoice'),
            ],
            'context': {
                'default_partner_id': self.id,
                'default_move_type': 'out_invoice',
            },
        }