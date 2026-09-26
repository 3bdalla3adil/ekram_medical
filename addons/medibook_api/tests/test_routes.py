# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

import jwt
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestMediBookAPIRoutes(HttpCase):
    """HTTP-level coverage for every MediBook API route."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = cls.env["medibook.organization"].create({
            "name": "Route Test Organization",
            "code": "ROUTE-TEST",
        })
        cls.clinic = cls.env["medibook.clinic"].create({
            "name": "Route Test Clinic",
            "organization_id": cls.org.id,
            "phone": "+97400000000",
        })
        cls.service = cls.env["medibook.service"].create({
            "name": "General Consultation",
            "code": "ROUTE-CONSULT",
            "clinic_id": cls.clinic.id,
            "duration_minutes": 30,
            "price": 100,
            "currency_id": cls.env.company.currency_id.id,
        })

        user_group = cls.env.ref("base.group_user")
        common = {
            "groups_id": [(6, 0, [user_group.id])],
            "medibook_organization_ids": [(6, 0, [cls.org.id])],
            "medibook_clinic_ids": [(6, 0, [cls.clinic.id])],
        }
        cls.patient_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            **common,
            "name": "Route Test Patient",
            "login": "route.patient@example.test",
            "email": "route.patient@example.test",
            "medibook_role": "patient",
        })
        cls.doctor_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            **common,
            "name": "Route Test Doctor",
            "login": "route.doctor@example.test",
            "email": "route.doctor@example.test",
            "medibook_role": "doctor",
        })
        cls.admin_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            **common,
            "name": "Route Test Admin",
            "login": "route.admin@example.test",
            "email": "route.admin@example.test",
            "medibook_role": "admin",
        })
        cls.reception_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            **common,
            "name": "Route Test Reception",
            "login": "route.reception@example.test",
            "email": "route.reception@example.test",
            "medibook_role": "reception",
        })

        cls.patient = cls.env["medibook.patient"].create({
            "user_id": cls.patient_user.id,
            "name": cls.patient_user.name,
            "medical_number": "MB-ROUTE-001",
            "organization_ids": [(6, 0, [cls.org.id])],
        })
        cls.doctor = cls.env["medibook.practitioner"].create({
            "user_id": cls.doctor_user.id,
            "specialization": "General Medicine",
            "license_number": "ROUTE-LIC-001",
            "clinic_ids": [(6, 0, [cls.clinic.id])],
        })
        cls.clinic.write({
            "practitioner_ids": [(6, 0, [cls.doctor.id])],
            "service_ids": [(6, 0, [cls.service.id])],
        })

        cls.appointment = cls.env["medibook.appointment"].create({
            "patient_id": cls.patient.id,
            "practitioner_id": cls.doctor.id,
            "clinic_id": cls.clinic.id,
            "service_id": cls.service.id,
            "starts_at": datetime(2035, 1, 10, 9, 0, 0),
            "duration_minutes": 30,
        })
        cls.consultation = cls.env["medibook.consultation"].create({
            "appointment_id": cls.appointment.id,
            "started_at": datetime(2035, 1, 10, 9, 0, 0),
            "status": "completed",
            "note": "Route test note",
            "diagnosis": "Route test diagnosis",
        })
        cls.record = cls.env["medibook.medical.record"].create({
            "patient_id": cls.patient.id,
            "consultation_id": cls.consultation.id,
            "entry_type": "consultation",
            "summary": "Route test medical record",
        })
        cls.prescription = cls.env["medibook.prescription"].create({
            "consultation_id": cls.consultation.id,
            "status": "issued",
        })
        cls.env["medibook.prescription.item"].create({
            "prescription_id": cls.prescription.id,
            "medication_id": "MED-ROUTE-001",
            "medication_name": "Route Test Medicine",
            "dose": "500 mg",
            "route": "oral",
            "frequency": "twice daily",
            "duration": "5 days",
            "quantity": 10,
            "instructions": "After food",
        })

        cls.env["ir.config_parameter"].sudo().set_param(
            "medibook.jwt_secret", "route-test-secret"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "medibook.firebase_project_id", "route-test-project"
        )

    def _token(self, user, jti=None):
        jti = jti or "route-test-jti-%s-%s" % (user.id, self.id())
        now = datetime.utcnow()
        self.env["medibook.auth.session"].sudo().create({
            "user_id": user.id,
            "jti": jti,
            "expires_at": now + timedelta(hours=1),
        })
        return jwt.encode({
            "sub": str(user.id),
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iss": "medibook",
        }, "route-test-secret", algorithm="HS256")

    def _request_json(self, path, method="GET", user=None, payload=None, headers=None):
        request_headers = {"Accept": "application/json"}
        if user:
            request_headers["Authorization"] = "Bearer %s" % self._token(user)
        request_headers.update(headers or {})
        data = None
        if payload is not None:
            request_headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        req = Request(
            self.base_url() + path,
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            response = self.url_open(req)
            return response.status, json.loads(response.read().decode())
        except HTTPError as error:
            return error.code, json.loads(error.read().decode())

    def test_01_auth_exchange_route(self):
        claims = {
            "sub": "firebase-route-test",
            "email": self.patient_user.email,
            "name": self.patient_user.name,
        }
        with patch(
            "odoo.addons.medibook_api.controllers.auth.MediBookAuth._verify_firebase",
            return_value=claims,
        ):
            status, body = self._request_json(
                "/medibook/api/auth/exchange",
                method="POST",
                payload={"id_token": "fake-firebase-token"},
            )
        self.assertEqual(status, 200)
        self.assertIn("access_token", body["data"])
        self.assertTrue(body["data"]["session_id"])

    def test_02_auth_exchange_requires_token(self):
        status, body = self._request_json(
            "/medibook/api/auth/exchange",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "missing_id_token")

    def test_03_me_route(self):
        status, body = self._request_json("/medibook/api/auth/me", user=self.patient_user)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["id"], str(self.patient_user.id))

    def test_04_profile_alias_route(self):
        status, body = self._request_json("/medibook/api/profile", user=self.patient_user)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["email"], self.patient_user.email)

    def test_05_logout_route(self):
        token = self._token(self.patient_user)
        req = Request(
            self.base_url() + "/medibook/api/auth/logout",
            data=b"{}",
            headers={
                "Authorization": "Bearer %s" % token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        response = self.url_open(req)
        body = json.loads(response.read().decode())
        self.assertEqual(response.status, 200)
        self.assertTrue(body["data"]["logged_out"])

    def test_06_clinics_route(self):
        status, body = self._request_json("/medibook/api/clinics", user=self.patient_user)
        self.assertEqual(status, 200)
        self.assertIn(str(self.clinic.id), [item["id"] for item in body["data"]])

    def test_07_medical_services_route(self):
        status, body = self._request_json(
            "/medibook/api/medical-services", user=self.patient_user
        )
        self.assertEqual(status, 200)
        self.assertIn(str(self.service.id), [item["id"] for item in body["data"]])

    def test_08_services_alias_route_with_filter(self):
        status, body = self._request_json(
            "/medibook/api/services?clinic_id=%s" % self.clinic.id,
            user=self.patient_user,
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["id"], str(self.service.id))

    def test_09_doctors_route(self):
        status, body = self._request_json("/medibook/api/doctors", user=self.patient_user)
        self.assertEqual(status, 200)
        self.assertIn(str(self.doctor.id), [item["id"] for item in body["data"]])

    def test_10_appointments_get_route(self):
        status, body = self._request_json(
            "/medibook/api/appointments", user=self.patient_user
        )
        self.assertEqual(status, 200)
        self.assertIn(str(self.appointment.id), [item["id"] for item in body["data"]])

    def test_11_appointments_create_route_and_idempotency(self):
        payload = {
            "clinic_id": self.clinic.id,
            "doctor_id": self.doctor.id,
            "service_id": self.service.id,
            "starts_at": "2035-01-11 09:00:00",
        }
        headers = {"Idempotency-Key": "route-create-001"}
        status, body = self._request_json(
            "/medibook/api/appointments",
            "POST",
            self.patient_user,
            payload,
            headers,
        )
        self.assertEqual(status, 201)
        first_id = body["data"]["id"]

        status, body = self._request_json(
            "/medibook/api/appointments",
            "POST",
            self.patient_user,
            payload,
            headers,
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["data"]["id"], first_id)

    def test_12_appointment_patch_route(self):
        status, body = self._request_json(
            "/medibook/api/appointments/%s" % self.appointment.id,
            "PATCH",
            self.patient_user,
            {"version": self.appointment.version, "notes": "Updated by route test"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["id"], str(self.appointment.id))

    def test_13_appointment_patch_version_conflict(self):
        status, body = self._request_json(
            "/medibook/api/appointments/%s" % self.appointment.id,
            "PATCH",
            self.patient_user,
            {"version": 99999, "notes": "Should be rejected"},
        )
        self.assertEqual(status, 409)
        self.assertEqual(body["error"], "version_conflict")

    def test_14_appointment_cancel_route(self):
        appointment = self.env["medibook.appointment"].create({
            "patient_id": self.patient.id,
            "practitioner_id": self.doctor.id,
            "clinic_id": self.clinic.id,
            "service_id": self.service.id,
            "starts_at": datetime(2035, 1, 12, 9, 0, 0),
            "duration_minutes": 30,
        })
        status, body = self._request_json(
            "/medibook/api/appointments/%s/cancel" % appointment.id,
            "POST",
            self.patient_user,
            {"reason": "Route test cancellation"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["status"], "cancelled")

    def test_15_doctor_availability_route(self):
        status, body = self._request_json(
            "/medibook/api/doctors/%s/availability?date=2035-01-10" % self.doctor.id,
            user=self.patient_user,
        )
        self.assertEqual(status, 200)
        self.assertTrue(any(slot["booked"] for slot in body["data"]))

    def test_16_doctor_availability_requires_date(self):
        status, body = self._request_json(
            "/medibook/api/doctors/%s/availability" % self.doctor.id,
            user=self.patient_user,
        )
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "validation")

    def test_17_medical_record_route(self):
        status, body = self._request_json(
            "/medibook/api/patients/%s/medical-record" % self.patient.id,
            user=self.patient_user,
        )
        self.assertEqual(status, 200)
        self.assertIn(str(self.record.id), [item["id"] for item in body["data"]])

    def test_18_medical_record_denies_reception(self):
        status, body = self._request_json(
            "/medibook/api/patients/%s/medical-record" % self.patient.id,
            user=self.reception_user,
        )
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not_found")

    def test_19_consultations_route(self):
        status, body = self._request_json(
            "/medibook/api/consultations", user=self.patient_user
        )
        self.assertEqual(status, 200)
        self.assertIn(str(self.consultation.id), [item["id"] for item in body["data"]])

    def test_20_prescriptions_route(self):
        status, body = self._request_json(
            "/medibook/api/prescriptions", user=self.patient_user
        )
        self.assertEqual(status, 200)
        prescription = next(
            item for item in body["data"] if item["id"] == str(self.prescription.id)
        )
        self.assertEqual(prescription["items"][0]["medication_name"], "Route Test Medicine")

    def test_21_protected_route_without_token(self):
        status, body = self._request_json("/medibook/api/clinics")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "unauthorized")
