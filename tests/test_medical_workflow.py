# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date


class TestMedicalWorkflow(TransactionCase):
    """
    Test the core Ekram Medical Center workflow:
    Patient → Appointment → Consultation → Lab Request → Lab Result
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a doctor employee
        cls.doctor = cls.env['hr.employee'].create({
            'name': 'Dr. Test Doctor',
            'job_title': 'Doctor - General',
        })

        # Create a lab technician employee
        cls.technician = cls.env['hr.employee'].create({
            'name': 'Test Technician',
            'job_title': 'Lab Technician',
        })

        # Create a lab template
        cls.template_cbc = cls.env['medical.lab.template'].create({
            'name': 'Test CBC',
            'code': 'TCBC',
            'department': 'hematology',
            'sample_type': 'blood',
        })

        # Create template lines
        cls.env['medical.lab.template.line'].create([
            {
                'template_id': cls.template_cbc.id,
                'sequence': 10,
                'test_name': 'WBC',
                'unit': '10³/µL',
                'normal_range_text': '4.5 - 11.0',
                'normal_min': 4.5,
                'normal_max': 11.0,
                'result_type': 'numeric',
            },
            {
                'template_id': cls.template_cbc.id,
                'sequence': 20,
                'test_name': 'Hemoglobin',
                'unit': 'g/dL',
                'normal_range_text': '12.0 - 17.5',
                'normal_min': 12.0,
                'normal_max': 17.5,
                'result_type': 'numeric',
            },
        ])

    def _create_patient(self, name='Test Patient'):
        return self.env['res.partner'].create({
            'name': name,
            'is_patient': True,
            'gender': 'male',
            'date_of_birth': date(1990, 1, 1),
            'blood_group': 'o+',
            'phone': '+968 9000 0000',
        })

    # ── Patient Tests ─────────────────────────────────────────────────────

    def test_01_patient_creation_assigns_medical_number(self):
        """Patient creation should auto-assign a medical number."""
        patient = self._create_patient('Patient Number Test')
        self.assertTrue(patient.is_patient)
        self.assertTrue(patient.medical_number)
        self.assertTrue(patient.medical_number.startswith('PT'))

    def test_02_patient_age_computation(self):
        """Age should be computed correctly from date of birth."""
        patient = self._create_patient('Age Test Patient')
        patient.date_of_birth = date(1990, 1, 1)
        today = date.today()
        expected_age = today.year - 1990 - (
            (today.month, today.day) < (1, 1)
        )
        self.assertEqual(patient.age, expected_age)

    def test_03_patient_future_dob_raises_error(self):
        """Date of birth in the future should raise a ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Future DOB Patient',
                'is_patient': True,
                'date_of_birth': date(2099, 1, 1),
            })

    def test_04_non_patient_has_no_medical_number(self):
        """Non-patient partners should not get a medical number."""
        partner = self.env['res.partner'].create({
            'name': 'Regular Company',
            'is_patient': False,
        })
        self.assertFalse(partner.medical_number)

    # ── Appointment Tests ─────────────────────────────────────────────────

    def test_05_appointment_creation_assigns_sequence(self):
        """Appointment should get a reference number on creation."""
        patient = self._create_patient()
        appointment = self.env['medical.appointment'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'appointment_type': 'consultation',
        })
        self.assertNotEqual(appointment.name, '/')
        self.assertIn('APT/', appointment.name)

    def test_06_appointment_workflow(self):
        """Test appointment state transitions."""
        patient = self._create_patient()
        appointment = self.env['medical.appointment'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'appointment_type': 'consultation',
        })
        self.assertEqual(appointment.state, 'draft')

        appointment.action_confirm()
        self.assertEqual(appointment.state, 'confirmed')

        appointment.action_start()
        self.assertEqual(appointment.state, 'in_progress')

        appointment.action_done()
        self.assertEqual(appointment.state, 'done')

    def test_07_appointment_cancel_and_reset(self):
        """Test appointment cancellation and reset."""
        patient = self._create_patient()
        appointment = self.env['medical.appointment'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'appointment_type': 'consultation',
        })
        appointment.action_cancel()
        self.assertEqual(appointment.state, 'cancelled')

        appointment.action_reset_draft()
        self.assertEqual(appointment.state, 'draft')

    # ── Consultation Tests ────────────────────────────────────────────────

    def test_08_consultation_creation(self):
        """Consultation should be created with a sequence number."""
        patient = self._create_patient()
        consultation = self.env['medical.consultation'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
        })
        self.assertNotEqual(consultation.name, '/')
        self.assertIn('CON/', consultation.name)
        self.assertEqual(consultation.state, 'draft')

    def test_09_consultation_workflow(self):
        """Test consultation state transitions."""
        patient = self._create_patient()
        consultation = self.env['medical.consultation'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
        })
        consultation.action_start()
        self.assertEqual(consultation.state, 'in_progress')

        consultation.action_done()
        self.assertEqual(consultation.state, 'done')

    # ── Lab Request Tests ─────────────────────────────────────────────────

    def test_10_lab_request_creation(self):
        """Lab request should get a sequence number."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        self.assertNotEqual(lab_request.name, '/')
        self.assertIn('LAB/', lab_request.name)
        self.assertEqual(lab_request.state, 'draft')

    def test_11_lab_request_process_creates_results(self):
        """Processing a lab request should auto-create result records."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        lab_request.action_process()
        self.assertEqual(lab_request.state, 'processing')
        self.assertEqual(len(lab_request.result_ids), 1)

    def test_12_lab_result_lines_loaded_from_template(self):
        """Result lines should be loaded from the template."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        lab_request.action_process()
        result = lab_request.result_ids[0]
        self.assertEqual(len(result.line_ids), 2)
        test_names = result.line_ids.mapped('test_name')
        self.assertIn('WBC', test_names)
        self.assertIn('Hemoglobin', test_names)

    # ── Result Flag Tests ─────────────────────────────────────────────────

    def test_13_result_flag_normal(self):
        """Result within normal range should be flagged Normal."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        lab_request.action_process()
        result = lab_request.result_ids[0]
        wbc_line = result.line_ids.filtered(lambda l: l.test_name == 'WBC')
        wbc_line.result_value = '7.5'  # Within 4.5 - 11.0
        self.assertEqual(wbc_line.flag, 'normal')

    def test_14_result_flag_high(self):
        """Result above normal range should be flagged High."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        lab_request.action_process()
        result = lab_request.result_ids[0]
        wbc_line = result.line_ids.filtered(lambda l: l.test_name == 'WBC')
        wbc_line.result_value = '12.0'  # Above 11.0
        self.assertEqual(wbc_line.flag, 'high')

    def test_15_result_flag_low(self):
        """Result below normal range should be flagged Low."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        lab_request.action_process()
        result = lab_request.result_ids[0]
        wbc_line = result.line_ids.filtered(lambda l: l.test_name == 'WBC')
        wbc_line.result_value = '3.0'  # Below 4.5
        self.assertEqual(wbc_line.flag, 'low')

    def test_16_result_flag_critical(self):
        """Result critically outside range should be flagged Critical."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        lab_request.action_process()
        result = lab_request.result_ids[0]
        wbc_line = result.line_ids.filtered(lambda l: l.test_name == 'WBC')
        wbc_line.result_value = '2.0'  # More than 20% below 4.5 → critical
        self.assertEqual(wbc_line.flag, 'critical')

    def test_17_result_validation_completes_request(self):
        """Validating all results should mark the request as completed."""
        patient = self._create_patient()
        lab_request = self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'template_ids': [(4, self.template_cbc.id)],
        })
        lab_request.action_process()
        result = lab_request.result_ids[0]
        for line in result.line_ids:
            line.result_value = '7.0'
        result.action_validate()
        self.assertEqual(result.state, 'validated')
        self.assertEqual(lab_request.state, 'completed')

    # ── Smart Button Count Tests ──────────────────────────────────────────

    def test_18_patient_appointment_count(self):
        """Patient appointment count should reflect actual appointments."""
        patient = self._create_patient()
        self.assertEqual(patient.appointment_count, 0)

        self.env['medical.appointment'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'appointment_type': 'consultation',
        })
        patient.invalidate_recordset()
        self.assertEqual(patient.appointment_count, 1)

    def test_19_patient_lab_request_count(self):
        """Patient lab request count should reflect actual lab requests."""
        patient = self._create_patient()
        self.assertEqual(patient.lab_request_count, 0)

        self.env['medical.lab.request'].create({
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
        })
        patient.invalidate_recordset()
        self.assertEqual(patient.lab_request_count, 1)