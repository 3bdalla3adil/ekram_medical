# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import date, datetime


class MedicalDashboardController(http.Controller):

    @http.route('/ekram_medical/reception_data', type='json', auth='user')
    def reception_dashboard_data(self):
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end   = datetime.combine(date.today(), datetime.max.time())

        Appointment = request.env['medical.appointment']
        Partner     = request.env['res.partner']
        Invoice     = request.env['account.move']

        patients_today = Appointment.search_count([
            ('appointment_date', '>=', today_start),
            ('appointment_date', '<=', today_end),
        ])
        total_patients = Partner.search_count([('is_patient', '=', True)])
        appointments_today = Appointment.search_count([
            ('appointment_date', '>=', today_start),
            ('appointment_date', '<=', today_end),
        ])
        pending_appointments = Appointment.search_count([
            ('state', 'in', ['draft', 'confirmed']),
            ('appointment_date', '>=', today_start),
            ('appointment_date', '<=', today_end),
        ])
        invoices_today = Invoice.search_count([
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '=', date.today()),
        ])
        outstanding = Invoice.search_count([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('state', '=', 'posted'),
        ])

        today_apts = Appointment.search([
            ('appointment_date', '>=', today_start),
            ('appointment_date', '<=', today_end),
        ], order='appointment_date asc', limit=20)

        apt_list = []
        for a in today_apts:
            apt_list.append({
                'id': a.id,
                'name': a.name,
                'patient': a.patient_id.name,
                'patient_id': a.patient_id.id,
                'doctor': a.doctor_id.name if a.doctor_id else '-',
                'time': a.appointment_date.strftime('%H:%M') if a.appointment_date else '-',
                'type': dict(a._fields['appointment_type'].selection).get(a.appointment_type, ''),
                'state': a.state,
                'state_label': dict(a._fields['state'].selection).get(a.state, ''),
            })

        return {
            'kpis': {
                'patients_today': patients_today,
                'total_patients': total_patients,
                'appointments_today': appointments_today,
                'pending_appointments': pending_appointments,
                'invoices_today': invoices_today,
                'outstanding': outstanding,
            },
            'appointments': apt_list,
        }

    @http.route('/ekram_medical/doctor_data', type='json', auth='user')
    def doctor_dashboard_data(self):
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end   = datetime.combine(date.today(), datetime.max.time())

        employee = request.env['hr.employee'].search(
            [('user_id', '=', request.env.uid)], limit=1
        )
        Consultation = request.env['medical.consultation']
        LabRequest   = request.env['medical.lab.request']
        Appointment  = request.env['medical.appointment']

        domain_doctor = [('doctor_id', '=', employee.id)] if employee else []

        today_consultations = Consultation.search_count(
            domain_doctor + [
                ('consultation_date', '>=', today_start),
                ('consultation_date', '<=', today_end),
            ]
        )
        pending_consultations = Consultation.search_count(
            domain_doctor + [('state', 'in', ['draft', 'in_progress'])]
        )
        completed_today = Consultation.search_count(
            domain_doctor + [
                ('state', '=', 'done'),
                ('consultation_date', '>=', today_start),
                ('consultation_date', '<=', today_end),
            ]
        )
        pending_labs = LabRequest.search_count(
            domain_doctor + [('state', 'in', ['draft', 'processing'])]
        )

        today_apts = Appointment.search(
            domain_doctor + [
                ('appointment_date', '>=', today_start),
                ('appointment_date', '<=', today_end),
            ], order='appointment_date asc', limit=20
        )

        patient_list = []
        for a in today_apts:
            patient_list.append({
                'id': a.id,
                'appointment_id': a.id,
                'consultation_id': a.consultation_id.id if a.consultation_id else False,
                'patient': a.patient_id.name,
                'patient_id': a.patient_id.id,
                'medical_number': a.patient_id.medical_number or '-',
                'time': a.appointment_date.strftime('%H:%M') if a.appointment_date else '-',
                'type': dict(a._fields['appointment_type'].selection).get(a.appointment_type, ''),
                'state': a.state,
                'state_label': dict(a._fields['state'].selection).get(a.state, ''),
                'has_consultation': bool(a.consultation_id),
            })

        pending_list = Consultation.search(
            domain_doctor + [('state', 'in', ['draft', 'in_progress'])],
            order='consultation_date asc', limit=10
        )
        pending_cons = []
        for c in pending_list:
            pending_cons.append({
                'id': c.id,
                'name': c.name,
                'patient': c.patient_id.name,
                'patient_id': c.patient_id.id,
                'date': c.consultation_date.strftime('%d/%m %H:%M') if c.consultation_date else '-',
                'state': c.state,
                'state_label': dict(c._fields['state'].selection).get(c.state, ''),
            })

        return {
            'doctor_name': employee.name if employee else request.env.user.name,
            'kpis': {
                'today_consultations': today_consultations,
                'pending_consultations': pending_consultations,
                'completed_today': completed_today,
                'pending_labs': pending_labs,
            },
            'today_patients': patient_list,
            'pending_consultations_list': pending_cons,
        }

    @http.route('/ekram_medical/lab_data', type='json', auth='user')
    def lab_dashboard_data(self):
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end   = datetime.combine(date.today(), datetime.max.time())

        LabRequest = request.env['medical.lab.request']
        LabResult  = request.env['medical.lab.result']

        pending_requests = LabRequest.search_count([
            ('state', 'in', ['draft', 'processing'])
        ])
        completed_today = LabRequest.search_count([
            ('state', '=', 'completed'),
            ('request_date', '>=', today_start),
            ('request_date', '<=', today_end),
        ])
        in_progress = LabRequest.search_count([('state', '=', 'processing')])
        pending_results = LabResult.search_count([('state', '=', 'draft')])

        pending_list = LabRequest.search([
            ('state', 'in', ['draft', 'processing'])
        ], order='priority desc, request_date asc', limit=20)

        req_list = []
        for r in pending_list:
            req_list.append({
                'id': r.id,
                'name': r.name,
                'patient': r.patient_id.name,
                'patient_id': r.patient_id.id,
                'doctor': r.doctor_id.name if r.doctor_id else '-',
                'time': r.request_date.strftime('%H:%M') if r.request_date else '-',
                'date': r.request_date.strftime('%d/%m/%Y') if r.request_date else '-',
                'priority': r.priority,
                'state': r.state,
                'state_label': dict(r._fields['state'].selection).get(r.state, ''),
                'investigations': ', '.join(r.template_ids.mapped('name')),
                'result_count': r.result_count,
            })

        pending_results_list = LabResult.search(
            [('state', '=', 'draft')], order='id asc', limit=10
        )
        res_list = []
        for res in pending_results_list:
            res_list.append({
                'id': res.id,
                'name': res.name,
                'patient': res.patient_id.name,
                'investigation': res.template_id.name if res.template_id else '-',
                'technician': res.technician_id.name if res.technician_id else '-',
                'date': res.result_date.strftime('%d/%m %H:%M') if res.result_date else '-',
            })

        return {
            'kpis': {
                'pending_requests': pending_requests,
                'completed_today': completed_today,
                'in_progress': in_progress,
                'pending_results': pending_results,
            },
            'pending_requests_list': req_list,
            'pending_results_list': res_list,
        }