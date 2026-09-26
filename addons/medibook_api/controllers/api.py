import json
import uuid
from datetime import timedelta

import jwt

from odoo import _, fields, http
from odoo.exceptions import AccessDenied, ValidationError
from odoo.http import request


class MediBookAPI(http.Controller):
    def _json(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _auth(self):
        raw = request.httprequest.headers.get('Authorization', '')
        if not raw.lower().startswith('bearer '):
            raise AccessDenied(_('Missing bearer token.'))
        secret = request.env['ir.config_parameter'].sudo().get_param('medibook.jwt_secret')
        if not secret:
            raise AccessDenied(_('MediBook JWT secret is not configured.'))
        try:
            claims = jwt.decode(raw.split(' ', 1)[1].strip(), secret, algorithms=['HS256'], issuer='medibook')
            uid = int(claims['sub'])
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise AccessDenied(_('Invalid or expired session.')) from exc
        session = request.env['medibook.auth.session'].sudo().search([
            ('jti', '=', claims.get('jti')), ('user_id', '=', uid),
            ('revoked', '=', False), ('expires_at', '>', fields.Datetime.now()),
        ], limit=1)
        user = request.env['res.users'].sudo().browse(uid).exists()
        if not session or not user or not user.active:
            raise AccessDenied(_('Session expired or revoked.'))
        session.write({'last_used_at': fields.Datetime.now()})
        request.update_env(user=user.id)
        return user

    def _audit(self, action, model=None, record_id=None, organization=None):
        request.env['medibook.audit.event'].sudo().create({
            'actor_id': request.env.user.id,
            'organization_id': organization.id if organization else False,
            'action': action, 'target_model': model, 'target_id': record_id,
            'outcome': 'success',
            'correlation_id': request.httprequest.headers.get('X-Correlation-ID') or uuid.uuid4().hex,
        })

    def _appointment_json(self, a):
        return {
            'id': str(a.id), 'patient_id': str(a.patient_id.id),
            'doctor_id': str(a.practitioner_id.id), 'clinic_id': str(a.clinic_id.id),
            'service_id': str(a.service_id.id),
            'starts_at': fields.Datetime.to_string(a.starts_at),
            'duration_minutes': a.duration_minutes, 'status': a.status,
            'version': a.version, 'is_telehealth': a.is_telehealth, 'notes': a.notes,
        }

    @http.route(['/medibook/api/auth/me', '/medibook/api/profile'], type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def me(self, **kw):
        try:
            user = self._auth()
            org = user.medibook_organization_ids[:1]
            return self._json({'data': {
                'id': str(user.id), 'display_name': user.name, 'email': user.email,
                'roles': [user.medibook_role],
                'organization_id': str(org.id) if org else None,
                'clinic_ids': [str(x) for x in user.medibook_clinic_ids.ids],
                'locale': user.lang or 'ar',
            }})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)

    @http.route('/medibook/api/auth/logout', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def logout(self, **kw):
        try:
            self._auth()
            raw = request.httprequest.headers.get('Authorization', '').split(' ', 1)[-1]
            secret = request.env['ir.config_parameter'].sudo().get_param('medibook.jwt_secret')
            claims = jwt.decode(raw, secret, algorithms=['HS256'], issuer='medibook')
            request.env['medibook.auth.session'].sudo().search([('jti', '=', claims['jti'])], limit=1).write({'revoked': True})
            return self._json({'data': {'logged_out': True}})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)

    @http.route('/medibook/api/clinics', type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def clinics(self, **kw):
        try:
            user = self._auth()
            records = request.env['medibook.clinic'].search([
                ('active', '=', True),
                ('organization_id', 'in', user.medibook_organization_ids.ids)
            ], order='name')
            return self._json({'data': [
                {'id': str(x.id), 'name': x.name, 'organization_id': str(x.organization_id.id), 'timezone': x.timezone}
                for x in records
            ]})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)

    @http.route(['/medibook/api/medical-services', '/medibook/api/services'], type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def services(self, **kw):
        try:
            user = self._auth()
            records = request.env['medibook.service'].search([
                ('active', '=', True),
                ('clinic_id.organization_id', 'in', user.medibook_organization_ids.ids)
            ], order='name')
            return self._json({'data': [
                {'id': str(x.id), 'name': x.name, 'code': x.code, 'clinic_id': str(x.clinic_id.id),
                 'duration_minutes': x.duration_minutes, 'price': x.price}
                for x in records
            ]})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)

    @http.route('/medibook/api/doctors', type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def doctors(self, **kw):
        try:
            user = self._auth()
            records = request.env['medibook.practitioner'].search([
                ('active', '=', True),
                ('clinic_ids.organization_id', 'in', user.medibook_organization_ids.ids)
            ], order='display_name')
            return self._json({'data': [
                {'id': str(x.id), 'name': x.display_name, 'specialization': x.specialization,
                 'license_number': x.license_number, 'clinic_ids': [str(c.id) for c in x.clinic_ids.ids]}
                for x in records
            ]})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)

    @http.route('/medibook/api/appointments', type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def appointments(self, **kw):
        try:
            user = self._auth()
            if user.medibook_role == 'patient':
                patient = request.env['medibook.patient'].search([('user_id', '=', user.id)], limit=1)
                domain = [('patient_id', '=', patient.id)]
            elif user.medibook_role == 'doctor':
                doctor = request.env['medibook.practitioner'].search([('user_id', '=', user.id)], limit=1)
                domain = [('practitioner_id', '=', doctor.id)]
            else:
                domain = [('clinic_id.organization_id', 'in', user.medibook_organization_ids.ids)]
            records = request.env['medibook.appointment'].search(domain, order='starts_at desc')
            return self._json({'data': [self._appointment_json(x) for x in records]})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)

    @http.route('/medibook/api/appointments', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def create_appointment(self, **kw):
        try:
            self._auth()
            body = json.loads(request.httprequest.data or '{}')
            body['_idempotency_key'] = request.httprequest.headers.get('Idempotency-Key') or body.get('idempotency_key')
            record = request.env['medibook.appointment'].create_from_api(body)
            self._audit('appointment.create', 'medibook.appointment', record.id, record.clinic_id.organization_id)
            return self._json({'data': self._appointment_json(record)}, 201)
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)
        except ValidationError as exc:
            return self._json({'error': 'validation', 'message': str(exc)}, 422)
        except Exception:
            return self._json({'error': 'internal_error'}, 500)

    @http.route('/medibook/api/appointments/<int:appointment_id>', type='http', auth='public', methods=['PATCH'], csrf=False, save_session=False)
    def update_appointment(self, appointment_id, **kw):
        try:
            user = self._auth()
            record = request.env['medibook.appointment'].browse(appointment_id).exists()
            if not record:
                return self._json({'error': 'not_found'}, 404)
            if not (record.patient_id.user_id == user or record.practitioner_id.user_id == user or record.clinic_id.organization_id in user.medibook_organization_ids):
                return self._json({'error': 'not_found'}, 404)
            body = json.loads(request.httprequest.data or '{}')
            if int(body.get('version', -1)) != record.version:
                return self._json({'error': 'version_conflict'}, 409)
            record.write({k: body[k] for k in ('notes',) if k in body})
            return self._json({'data': self._appointment_json(record)})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)
        except Exception:
            return self._json({'error': 'internal_error'}, 500)

    @http.route('/medibook/api/appointments/<int:appointment_id>/cancel', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def cancel(self, appointment_id, **kw):
        try:
            user = self._auth()
            record = request.env['medibook.appointment'].browse(appointment_id).exists()
            if not record:
                return self._json({'error': 'not_found'}, 404)
            if not (record.patient_id.user_id == user or record.practitioner_id.user_id == user or record.clinic_id.organization_id in user.medibook_organization_ids):
                return self._json({'error': 'not_found'}, 404)
            body = json.loads(request.httprequest.data or '{}')
            record.write({'status': 'cancelled', 'cancellation_reason': body.get('reason')})
            self._audit('appointment.cancel', 'medibook.appointment', record.id, record.clinic_id.organization_id)
            return self._json({'data': self._appointment_json(record)})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)

    @http.route('/medibook/api/doctors/<int:doctor_id>/availability', type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def availability(self, doctor_id, **kw):
        try:
            user = self._auth()
            doctor = request.env['medibook.practitioner'].browse(doctor_id).exists()
            if not doctor or not (doctor.clinic_ids & request.env['medibook.clinic'].search([('organization_id', 'in', user.medibook_organization_ids.ids)])):
                return self._json({'error': 'not_found'}, 404)
            day = request.params.get('date')
            if not day:
                return self._json({'error': 'validation', 'message': 'date is required'}, 422)
            start = fields.Datetime.to_datetime(day)
            end = start + timedelta(days=1)
            records = request.env['medibook.appointment'].search([
                ('practitioner_id', '=', doctor.id), ('starts_at', '>=', start),
                ('starts_at', '<', end), ('status', 'not in', ['cancelled', 'no_show'])
            ], order='starts_at')
            return self._json({'data': [
                {'starts_at': fields.Datetime.to_string(x.starts_at), 'duration_minutes': x.duration_minutes, 'booked': True}
                for x in records
            ]})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)
