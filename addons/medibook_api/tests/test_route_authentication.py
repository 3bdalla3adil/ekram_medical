# -*- coding: utf-8 -*-
import json
from urllib.error import HTTPError
from urllib.request import Request

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestMediBookRouteAuthentication(HttpCase):
    """Smoke-test authentication handling for every protected API route."""

    def _request(self, path, method="GET", payload=None):
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        req = Request(
            self.base_url() + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            response = self.url_open(req)
            return response.status, json.loads(response.read().decode())
        except HTTPError as error:
            return error.code, json.loads(error.read().decode())

    def test_every_protected_route_rejects_missing_bearer_token(self):
        routes = [
            ("/medibook/api/auth/me", "GET", None),
            ("/medibook/api/profile", "GET", None),
            ("/medibook/api/auth/logout", "POST", {}),
            ("/medibook/api/clinics", "GET", None),
            ("/medibook/api/medical-services", "GET", None),
            ("/medibook/api/services", "GET", None),
            ("/medibook/api/doctors", "GET", None),
            ("/medibook/api/appointments", "GET", None),
            ("/medibook/api/appointments", "POST", {}),
            ("/medibook/api/appointments/1", "PATCH", {}),
            ("/medibook/api/appointments/1/cancel", "POST", {}),
            ("/medibook/api/doctors/1/availability?date=2035-01-10", "GET", None),
            ("/medibook/api/patients/1/medical-record", "GET", None),
            ("/medibook/api/consultations", "GET", None),
            ("/medibook/api/prescriptions", "GET", None),
        ]

        for path, method, payload in routes:
            with self.subTest(path=path, method=method):
                status, body = self._request(path, method, payload)
                self.assertEqual(status, 401, "Unexpected status for %s" % path)
                self.assertEqual(body.get("error"), "unauthorized")

    def test_auth_exchange_route_rejects_missing_firebase_token(self):
        status, body = self._request(
            "/medibook/api/auth/exchange",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body.get("error"), "missing_id_token")
