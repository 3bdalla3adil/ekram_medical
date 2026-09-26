from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MedibookOrganization(models.Model):
    _name = 'medibook.organization'
    _description = 'MediBook Healthcare Organization'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True)
    timezone = fields.Char(default='Asia/Qatar', required=True)
    default_language = fields.Selection([('ar', 'Arabic'), ('en', 'English')], default='ar', required=True)
    active = fields.Boolean(default=True)
    clinic_ids = fields.One2many('medibook.clinic', 'organization_id')
    _sql_constraints = [('code_uniq', 'unique(code)', 'Organization code must be unique.')]


class MedibookClinic(models.Model):
    _name = 'medibook.clinic'
    _description = 'MediBook Clinic'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    organization_id = fields.Many2one('medibook.organization', required=True, ondelete='cascade', index=True)
    address = fields.Text()
    phone = fields.Char()
    timezone = fields.Char(related='organization_id.timezone', store=True)
    active = fields.Boolean(default=True)
    practitioner_ids = fields.Many2many('medibook.practitioner', string='Practitioners')
    service_ids = fields.Many2many('medibook.service', string='Services')


class MedibookPractitioner(models.Model):
    _name = 'medibook.practitioner'
    _description = 'MediBook Practitioner'
    _inherit = ['mail.thread']

    user_id = fields.Many2one('res.users', required=True, ondelete='restrict', index=True)
    display_name = fields.Char(related='user_id.name', store=True)
    specialization = fields.Char()
    license_number = fields.Char()
    bio = fields.Text()
    clinic_ids = fields.Many2many('medibook.clinic', string='Clinics')
    active = fields.Boolean(default=True)
    _sql_constraints = [('user_uniq', 'unique(user_id)', 'A user can have only one practitioner profile.')]


class MedibookService(models.Model):
    _name = 'medibook.service'
    _description = 'MediBook Medical Service'

    name = fields.Char(required=True)
    code = fields.Char(index=True)
    clinic_id = fields.Many2one('medibook.clinic', required=True, ondelete='cascade', index=True)
    duration_minutes = fields.Integer(default=30, required=True)
    price = fields.Monetary()
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id.id)
    active = fields.Boolean(default=True)
    _sql_constraints = [('duration_positive', 'CHECK(duration_minutes > 0)', 'Duration must be positive.')]


class MedibookPatient(models.Model):
    _name = 'medibook.patient'
    _description = 'MediBook Patient'
    _inherit = ['mail.thread']

    user_id = fields.Many2one('res.users', ondelete='restrict', index=True)
    name = fields.Char(required=True, tracking=True)
    medical_number = fields.Char(required=True, copy=False, index=True)
    date_of_birth = fields.Date()
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'), ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'), ('o+', 'O+'), ('o-', 'O-')
    ])
    allergies = fields.Text()
    chronic_conditions = fields.Text()
    organization_ids = fields.Many2many('medibook.organization', string='Organizations')
    active = fields.Boolean(default=True)
    _sql_constraints = [('medical_number_uniq', 'unique(medical_number)', 'Medical number must be unique.')]


class ResUsers(models.Model):
    _inherit = 'res.users'

    firebase_uid = fields.Char(index=True, copy=False)
    medibook_role = fields.Selection([
        ('patient', 'Patient'), ('doctor', 'Doctor'), ('admin', 'Clinic Admin'),
        ('billing', 'Billing'), ('reception', 'Reception'),
    ], default='patient', required=True, index=True)
    medibook_organization_ids = fields.Many2many('medibook.organization', string='MediBook Organizations')
    medibook_clinic_ids = fields.Many2many('medibook.clinic', string='MediBook Clinics')


class MedibookAuthSession(models.Model):
    _name = 'medibook.auth.session'
    _description = 'MediBook Auth Session'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    jti = fields.Char(required=True, copy=False, index=True)
    expires_at = fields.Datetime(required=True, index=True)
    revoked = fields.Boolean(default=False, index=True)
    last_used_at = fields.Datetime()
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    _sql_constraints = [('jti_uniq', 'unique(jti)', 'Session token id must be unique.')]


class MedibookAppointment(models.Model):
    _name = 'medibook.appointment'
    _description = 'MediBook Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'starts_at desc'

    patient_id = fields.Many2one('medibook.patient', required=True, ondelete='restrict', index=True)
    practitioner_id = fields.Many2one('medibook.practitioner', required=True, ondelete='restrict', index=True)
    clinic_id = fields.Many2one('medibook.clinic', required=True, ondelete='restrict', index=True)
    service_id = fields.Many2one('medibook.service', required=True, ondelete='restrict')
    starts_at = fields.Datetime(required=True, index=True)
    duration_minutes = fields.Integer(default=30, required=True)
    status = fields.Selection([
        ('scheduled', 'Scheduled'), ('checked_in', 'Checked In'),
        ('in_consultation', 'In Consultation'), ('completed', 'Completed'),
        ('cancelled', 'Cancelled'), ('no_show', 'No Show')
    ], default='scheduled', required=True, index=True, tracking=True)
    is_telehealth = fields.Boolean()
    notes = fields.Text()
    cancellation_reason = fields.Text()
    version = fields.Integer(default=1, readonly=True)
    idempotency_key = fields.Char(index=True, copy=False)

    _sql_constraints = [('duration_positive', 'CHECK(duration_minutes > 0)', 'Duration must be positive.')]

    @api.constrains('practitioner_id', 'starts_at', 'duration_minutes', 'status')
    def _check_no_overlap(self):
        for rec in self:
            if rec.status in ('cancelled', 'no_show'):
                continue
            end = rec.starts_at + timedelta(minutes=rec.duration_minutes)
            conflicts = self.search([
                ('id', '!=', rec.id),
                ('practitioner_id', '=', rec.practitioner_id.id),
                ('status', 'not in', ['cancelled', 'no_show']),
                ('starts_at', '<', end),
            ])
            if any(c.starts_at + timedelta(minutes=c.duration_minutes) > rec.starts_at for c in conflicts):
                raise ValidationError(_('Doctor is already booked during this time.'))

    def write(self, vals):
        if any(k in vals for k in ('patient_id', 'practitioner_id', 'clinic_id', 'service_id', 'starts_at', 'duration_minutes')):
            vals = dict(vals)
            vals['version'] = max(self.mapped('version') or [1]) + 1
        return super().write(vals)

    @api.model
    def create_from_api(self, body):
        clinic = self.env['medibook.clinic'].browse(int(body.get('clinic_id') or 0)).exists()
        doctor = self.env['medibook.practitioner'].browse(int(body.get('doctor_id') or 0)).exists()
        service = self.env['medibook.service'].browse(int(body.get('service_id') or 0)).exists()
        if not clinic or not doctor or not service or not body.get('starts_at'):
            raise ValidationError(_('clinic_id, doctor_id, service_id and starts_at are required.'))
        if clinic not in doctor.clinic_ids or service.clinic_id != clinic:
            raise ValidationError(_('Doctor/service is not available at this clinic.'))
        if self.env.user.medibook_role == 'patient':
            patient = self.env['medibook.patient'].search([('user_id', '=', self.env.user.id)], limit=1)
        else:
            patient = self.env['medibook.patient'].browse(int(body.get('patient_id') or 0)).exists()
        if not patient:
            raise ValidationError(_('Patient profile is required.'))
        key = body.get('_idempotency_key')
        if key:
            existing = self.search([('idempotency_key', '=', key)], limit=1)
            if existing:
                return existing
        return self.create({
            'patient_id': patient.id,
            'clinic_id': clinic.id,
            'practitioner_id': doctor.id,
            'service_id': service.id,
            'starts_at': body['starts_at'],
            'duration_minutes': int(body.get('duration_minutes') or service.duration_minutes or 30),
            'is_telehealth': bool(body.get('is_telehealth')),
            'notes': body.get('notes'),
            'idempotency_key': key,
        })


class MedibookAuditEvent(models.Model):
    _name = 'medibook.audit.event'
    _description = 'MediBook Audit Event'
    _order = 'created_at desc'

    actor_id = fields.Many2one('res.users', required=True, index=True, ondelete='restrict')
    organization_id = fields.Many2one('medibook.organization', index=True, ondelete='restrict')
    action = fields.Char(required=True, index=True)
    target_model = fields.Char(index=True)
    target_id = fields.Integer(index=True)
    outcome = fields.Selection([('success', 'Success'), ('denied', 'Denied'), ('error', 'Error')], required=True)
    correlation_id = fields.Char(index=True)
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
