import json
import time
import uuid
from datetime import timedelta

import jwt
import requests

from odoo import _, fields, http
from odoo.exceptions import AccessDenied
from odoo.http import request


class MediBookAuth(http.Controller):
    def _json(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _certs(self):
        params = request.env['ir.config_parameter'].sudo()
        cached = params.get_param('medibook.firebase_certs')
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass
        response = requests.get(
            'https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com',
            timeout=10,
        )
        response.raise_for_status()
        certs = response.json()
        params.set_param('medibook.firebase_certs', json.dumps(certs))
        return certs

    def _verify_firebase(self, token):
        project = request.env['ir.config_parameter'].sudo().get_param('medibook.firebase_project_id')
        if not project:
            raise AccessDenied(_('Firebase project is not configured.'))
        try:
            header = jwt.get_unverified_header(token)
            cert = self._certs().get(header.get('kid'))
            if not cert:
                request.env['ir.config_parameter'].sudo().set_param('medibook.firebase_certs', '')
                cert = self._certs().get(header.get('kid'))
            if not cert:
                raise AccessDenied(_('Unknown Firebase signing key.'))
            return jwt.decode(
                token, cert, algorithms=['RS256'], audience=project,
                issuer=f'https://securetoken.google.com/{project}',
                options={'require': ['exp', 'iat', 'sub']},
            )
        except (jwt.InvalidTokenError, requests.RequestException, ValueError) as exc:
            raise AccessDenied(_('Invalid Firebase identity token.')) from exc

    def _issue(self, user):
        now = int(time.time())
        ttl = int(request.env['ir.config_parameter'].sudo().get_param('medibook.jwt_ttl_seconds', '900'))
        secret = request.env['ir.config_parameter'].sudo().get_param('medibook.jwt_secret')
        if not secret:
            raise AccessDenied(_('MediBook JWT secret is not configured.'))
        jti = uuid.uuid4().hex
        token = jwt.encode(
            {'sub': str(user.id), 'jti': jti, 'iat': now, 'exp': now + ttl, 'iss': 'medibook'},
            secret, algorithm='HS256'
        )
        session = request.env['medibook.auth.session'].sudo().create({
            'user_id': user.id, 'jti': jti,
            'expires_at': fields.Datetime.now() + timedelta(seconds=ttl),
        })
        return token, session, now + ttl

    @http.route('/medibook/api/auth/exchange', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def exchange(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
            token = body.get('id_token')
            if not token:
                return self._json({'error': 'missing_id_token'}, 400)
            claims = self._verify_firebase(token)
            uid, email = claims['sub'], claims.get('email')
            users = request.env['res.users'].sudo()
            user = users.search([('firebase_uid', '=', uid)], limit=1)
            if not user and email:
                user = users.search([('login', '=', email)], limit=1)
            if not user:
                user = users.with_context(no_reset_password=True).create({
                    'name': claims.get('name') or email or 'MediBook User',
                    'login': email or f'{uid}@firebase.local',
                    'email': email, 'firebase_uid': uid,
                    'medibook_role': 'patient',
                    'groups_id': [(6, 0, [request.env.ref('base.group_user').id])],
                })
            if not user.active:
                return self._json({'error': 'account_deactivated'}, 403)
            access, session, exp = self._issue(user)
            org = user.medibook_organization_ids[:1]
            return self._json({'data': {
                'access_token': access, 'refresh_token': None,
                'access_expires_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(exp)),
                'refresh_expires_at': None, 'session_id': session.jti,
                'user': {
                    'id': str(user.id), 'display_name': user.name, 'email': user.email,
                    'roles': [user.medibook_role],
                    'organization_id': str(org.id) if org else None,
                    'clinic_ids': [str(x) for x in user.medibook_clinic_ids.ids],
                    'locale': user.lang or 'ar',
                },
            }})
        except AccessDenied as exc:
            return self._json({'error': 'unauthorized', 'message': str(exc)}, 401)
        except Exception:
            return self._json({'error': 'internal_error'}, 500)
