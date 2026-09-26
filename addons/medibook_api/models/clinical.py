from odoo import fields, models, _
from odoo.exceptions import ValidationError


class MedibookConsultation(models.Model):
    _name = 'medibook.consultation'
    _description = 'MediBook Consultation'
    _inherit = ['mail.thread']

    appointment_id = fields.Many2one('medibook.appointment', required=True, ondelete='restrict', index=True)
    patient_id = fields.Many2one(related='appointment_id.patient_id', store=True)
    practitioner_id = fields.Many2one(related='appointment_id.practitioner_id', store=True)
    started_at = fields.Datetime()
    completed_at = fields.Datetime()
    status = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('signed', 'Signed')
    ], default='draft', required=True, tracking=True)
    note = fields.Text()
    diagnosis = fields.Text()

    def write(self, vals):
        for rec in self:
            if rec.status == 'signed' and any(k in vals for k in ('note', 'diagnosis', 'appointment_id')):
                raise ValidationError(_('Signed consultations are immutable.'))
        return super().write(vals)


class MedibookMedicalRecord(models.Model):
    _name = 'medibook.medical.record'
    _description = 'MediBook Medical Record'
    _inherit = ['mail.thread']
    _order = 'created_at desc'

    patient_id = fields.Many2one('medibook.patient', required=True, ondelete='restrict', index=True)
    consultation_id = fields.Many2one('medibook.consultation', ondelete='restrict')
    entry_type = fields.Selection([
        ('consultation', 'Consultation'), ('diagnosis', 'Diagnosis'),
        ('prescription', 'Prescription'), ('lab', 'Lab')
    ], required=True)
    summary = fields.Text(required=True)
    supersedes_id = fields.Many2one('medibook.medical.record', ondelete='restrict')
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    def write(self, vals):
        raise ValidationError(_('Medical records are append-only.'))

    def unlink(self):
        raise ValidationError(_('Medical records cannot be deleted.'))


class MedibookPrescription(models.Model):
    _name = 'medibook.prescription'
    _description = 'MediBook Prescription'
    _inherit = ['mail.thread']

    consultation_id = fields.Many2one('medibook.consultation', required=True, ondelete='restrict', index=True)
    patient_id = fields.Many2one(related='consultation_id.patient_id', store=True)
    prescriber_id = fields.Many2one(related='consultation_id.practitioner_id', store=True)
    issued_at = fields.Datetime(default=fields.Datetime.now)
    status = fields.Selection([
        ('draft', 'Draft'), ('issued', 'Issued'), ('cancelled', 'Cancelled'), ('expired', 'Expired')
    ], default='draft', required=True, tracking=True)
    item_ids = fields.One2many('medibook.prescription.item', 'prescription_id')


class MedibookPrescriptionItem(models.Model):
    _name = 'medibook.prescription.item'
    _description = 'MediBook Prescription Item'

    prescription_id = fields.Many2one('medibook.prescription', required=True, ondelete='cascade')
    medication_id = fields.Char(required=True)
    medication_name = fields.Char(required=True)
    dose = fields.Char()
    route = fields.Char()
    frequency = fields.Char()
    duration = fields.Char()
    quantity = fields.Integer()
    instructions = fields.Text()
