# MediBook Odoo 19 Backend

This repository now contains the MediBook headless API as a separate Odoo addon under `addons/medibook_api`.

## Authentication

Flutter authenticates with Firebase and sends the Firebase ID token to:

POST /medibook/api/auth/exchange

Odoo verifies the Firebase JWT and issues a short-lived MediBook JWT. Protected endpoints use:

Authorization: Bearer <MediBook JWT>

Configure Odoo system parameters:

- medibook.firebase_project_id
- medibook.jwt_secret

The default access-token TTL is 900 seconds.

## API

- GET /medibook/api/auth/me
- GET /medibook/api/profile
- POST /medibook/api/auth/logout
- GET /medibook/api/clinics
- GET /medibook/api/medical-services
- GET /medibook/api/services
- GET /medibook/api/doctors
- GET /medibook/api/appointments
- POST /medibook/api/appointments
- PATCH /medibook/api/appointments/<id>
- POST /medibook/api/appointments/<id>/cancel
- GET /medibook/api/doctors/<id>/availability?date=...

Appointment creation supports Idempotency-Key and updates use optimistic version checking.

This backend is an integration layer, not a declaration of regulatory compliance. Production deployment still requires secrets management, backups, rate limiting, monitoring, privacy/retention controls, concurrency testing, and security assessment.
