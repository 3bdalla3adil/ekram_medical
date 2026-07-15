import json
from odoo import http
from odoo.http import request
from datetime import date, timedelta


class MedicalDashboard(http.Controller):

    @http.route('/ekram_medical/reception_data', type='json', auth='user')
    def reception_data(self):
        today = date.today()
        Appt = request.env['medical.appointment']
        Partner = request.env['res.partner']
        Invoice = request.env['account.move']
        LabReq = request.env['medical.lab.request']

        today_appts = Appt.search([
            ('appointment_date', '>=', str(today)),
            ('appointment_date', '<', str(today + timedelta(days=1))),
        ])
        return {
            'kpis': {
                'patients_total': Partner.search_count([('is_patient', '=', True)]),
                'appointments_today': len(today_appts),
                'lab_requests_pending': LabReq.search_count([('state', '=', 'pending')]),
                'invoices_outstanding': Invoice.search_count([
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', 'not in', ['paid', 'in_payment']),
                    ('state', '=', 'posted'),
                ]),
            },
            'appointments': [{
                'id': a.id,
                'name': a.name,
                'patient': a.patient_id.name,
                'time': a.appointment_date.strftime('%H:%M') if a.appointment_date else '',
                'type': dict(a._fields['appointment_type'].selection).get(a.appointment_type, ''),
                'state': a.state,
            } for a in today_appts.sorted('appointment_date')],
        }

    @http.route('/ekram_medical/lab_data', type='json', auth='user')
    def lab_data(self):
        LabReq = request.env['medical.lab.request']
        pending = LabReq.search([('state', '=', 'pending')], limit=20)
        in_progress = LabReq.search([('state', '=', 'in_progress')], limit=20)
        return {
            'kpis': {
                'pending': LabReq.search_count([('state', '=', 'pending')]),
                'in_progress': LabReq.search_count([('state', '=', 'in_progress')]),
                'completed_today': LabReq.search_count([
                    ('state', '=', 'completed'),
                    ('validated_date', '>=', str(date.today())),
                ]),
                'critical': LabReq.search_count([('has_critical', '=', True),
                                                  ('state', '=', 'completed')]),
            },
            'pending_requests': [{
                'id': r.id,
                'name': r.name,
                'patient': r.patient_id.name,
                'priority': r.priority,
                'investigations': ', '.join(r.template_ids.mapped('code')),
                'date': r.request_date.strftime('%Y-%m-%d %H:%M') if r.request_date else '',
            } for r in pending],
            'in_progress_requests': [{
                'id': r.id,
                'name': r.name,
                'patient': r.patient_id.name,
                'investigations': ', '.join(r.template_ids.mapped('code')),
                'lines_filled': len(r.result_line_ids.filtered(lambda l: l.result_value)),
                'lines_total': len(r.result_line_ids),
            } for r in in_progress],
        }

    @http.route('/ekram_medical/admin_data', type='json', auth='user')
    def admin_data(self):
        Invoice = request.env['account.move']
        Partner = request.env['res.partner']
        LabReq = request.env['medical.lab.request']
        today = date.today()
        month_start = today.replace(day=1)

        posted_invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ])
        month_invoices = posted_invoices.filtered(
            lambda i: i.invoice_date and i.invoice_date >= month_start
        )
        total_revenue = sum(month_invoices.mapped('amount_total'))
        total_paid = sum(month_invoices.filtered(
            lambda i: i.payment_state in ('paid', 'in_payment')
        ).mapped('amount_total'))
        outstanding = sum(posted_invoices.filtered(
            lambda i: i.payment_state not in ('paid', 'in_payment')
        ).mapped('amount_residual'))

        # 6-month revenue
        revenue_chart = []
        for i in range(5, -1, -1):
            d = today.replace(day=1) - timedelta(days=i * 28)
            ms = d.replace(day=1)
            if ms.month == 12:
                me = ms.replace(year=ms.year + 1, month=1, day=1)
            else:
                me = ms.replace(month=ms.month + 1, day=1)
            inv = posted_invoices.filtered(
                lambda x, s=ms, e=me: x.invoice_date and s <= x.invoice_date < e
            )
            revenue_chart.append({
                'month': ms.strftime('%b %Y'),
                'amount': sum(inv.mapped('amount_total')),
            })

        # Journal balances
        journals = request.env['account.journal'].search([
            ('type', 'in', ('cash', 'bank'))
        ])
        journal_data = []
        for j in journals:
            journal_data.append({
                'name': j.name,
                'type': j.type,
                'balance': j.current_statement_balance if hasattr(j, 'current_statement_balance') else 0,
            })

        return {
            'kpis': {
                'revenue_month': total_revenue,
                'outstanding': outstanding,
                'collection_rate': round((total_paid / total_revenue * 100) if total_revenue else 0, 1),
                'patients_total': Partner.search_count([('is_patient', '=', True)]),
                'lab_completed_today': LabReq.search_count([
                    ('state', '=', 'completed'),
                    ('validated_date', '>=', str(today)),
                ]),
                'critical_flags': LabReq.search_count([('has_critical', '=', True)]),
            },
            'revenue_chart': revenue_chart,
            'journals': journal_data,
            'recent_invoices': [{
                'name': i.name,
                'partner': i.partner_id.name,
                'amount': i.amount_total,
                'date': str(i.invoice_date),
                'state': i.payment_state,
            } for i in posted_invoices.sorted('invoice_date', reverse=True)[:15]],
        }