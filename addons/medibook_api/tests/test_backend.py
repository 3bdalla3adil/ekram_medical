from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMediBookBackend(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = cls.env['medibook.organization'].create({'name': 'Test Clinic Group', 'code': 'TEST'})
        cls.clinic = cls.env['medibook.clinic'].create({'name': 'Test Clinic', 'organization_id': cls.org.id})
        cls.doctor_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'MediBook Doctor',
            'login': 'medibook-doctor-test@example.com',
            'medibook_role': 'doctor',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
            'medibook_organization_ids': [(6, 0, [cls.org.id])],
            'medibook_clinic_ids': [(6, 0, [cls.clinic.id])],
        })
        cls.doctor = cls.env['medibook.practitioner'].create({
            'user_id': cls.doctor_user.id,
            'specialization': 'General Medicine',
            'clinic_ids': [(6, 0, [cls.clinic.id])],
        })
        cls.patient = cls.env['medibook.patient'].create({
            'name': 'Test Patient',
            'medical_number': 'MB-TEST-001',
            'organization_ids': [(6, 0, [cls.org.id])],
        })
        cls.service = cls.env['medibook.service'].create({
            'name': 'Consultation', 'code': 'CONS', 'clinic_id': cls.clinic.id,
            'duration_minutes': 30,
        })

    def test_appointment_overlap_is_rejected(self):
        start = datetime.utcnow() + timedelta(days=1)
        values = {
            'patient_id': self.patient.id, 'practitioner_id': self.doctor.id,
            'clinic_id': self.clinic.id, 'service_id': self.service.id,
            'starts_at': start, 'duration_minutes': 30,
        }
        self.env['medibook.appointment'].create(values)
        with self.assertRaises(ValidationError):
            self.env['medibook.appointment'].create(dict(values, starts_at=start + timedelta(minutes=15)))

    def test_medical_record_is_append_only(self):
        record = self.env['medibook.medical.record'].create({
            'patient_id': self.patient.id, 'entry_type': 'diagnosis', 'summary': 'Initial note',
        })
        with self.assertRaises(ValidationError):
            record.write({'summary': 'Changed'})
        with self.assertRaises(ValidationError):
            record.unlink()
