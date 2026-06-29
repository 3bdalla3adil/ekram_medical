# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class MedicalAdminDashboardController(http.Controller):

    @http.route('/ekram_medical/admin_data', type='jsonrpc', auth='user')
    def admin_dashboard_data(self):
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end   = datetime.combine(today, datetime.max.time())
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        month_end_dt   = datetime.combine(today, datetime.max.time())

        # Last 6 months for chart
        months = []
        for i in range(5, -1, -1):
            d = today - relativedelta(months=i)
            months.append({'year': d.year, 'month': d.month, 'label': d.strftime('%b %Y')})

        Invoice     = request.env['account.move']
        Payment     = request.env['account.payment']
        Appointment = request.env['medical.appointment']
        Partner     = request.env['res.partner']
        LabRequest  = request.env['medical.lab.request']

        # ── Revenue KPIs ──────────────────────────────────────────────────
        month_invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', today),
        ])
        revenue_this_month = sum(month_invoices.mapped('amount_total'))
        revenue_paid_month = sum(
            inv.amount_total - inv.amount_residual for inv in month_invoices
        )

        today_invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '=', today),
        ])
        revenue_today = sum(today_invoices.mapped('amount_total'))

        outstanding_invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ])
        outstanding_amount = sum(outstanding_invoices.mapped('amount_residual'))
        outstanding_count  = len(outstanding_invoices)

        # ── Operational KPIs ──────────────────────────────────────────────
        total_patients     = Partner.search_count([('is_patient', '=', True)])
        patients_month     = Partner.search_count([
            ('is_patient', '=', True),
            ('create_date', '>=', month_start_dt),
            ('create_date', '<=', month_end_dt),
        ])
        appointments_today = Appointment.search_count([
            ('appointment_date', '>=', today_start),
            ('appointment_date', '<=', today_end),
        ])
        appointments_month = Appointment.search_count([
            ('appointment_date', '>=', month_start_dt),
            ('appointment_date', '<=', month_end_dt),
        ])
        lab_requests_today = LabRequest.search_count([
            ('request_date', '>=', today_start),
            ('request_date', '<=', today_end),
        ])
        lab_requests_month = LabRequest.search_count([
            ('request_date', '>=', month_start_dt),
            ('request_date', '<=', month_end_dt),
        ])

        # ── Revenue Chart: last 6 months ──────────────────────────────────
        revenue_chart = []
        for m in months:
            m_start = date(m['year'], m['month'], 1)
            m_end   = (m_start + relativedelta(months=1)) - timedelta(days=1)
            invs    = Invoice.search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', m_start),
                ('invoice_date', '<=', m_end),
            ])
            total     = sum(invs.mapped('amount_total'))
            collected = sum(inv.amount_total - inv.amount_residual for inv in invs)
            revenue_chart.append({
                'label':     m['label'],
                'total':     round(total, 3),
                'collected': round(collected, 3),
            })

        # ── Cash / Bank Journals ──────────────────────────────────────────
        Journal = request.env['account.journal']

        def journal_balance(journals):
            result = []
            for j in journals:
                payments = Payment.search([
                    ('journal_id', '=', j.id),
                    ('state', '=', 'posted'),
                    ('date', '>=', month_start),
                    ('date', '<=', today),
                ])
                inbound  = sum(p.amount for p in payments if p.payment_type == 'inbound')
                outbound = sum(p.amount for p in payments if p.payment_type == 'outbound')
                result.append({
                    'name':     j.name,
                    'inbound':  round(inbound, 3),
                    'outbound': round(outbound, 3),
                    'net':      round(inbound - outbound, 3),
                })
            return result

        cash_data = journal_balance(Journal.search([('type', '=', 'cash')]))
        bank_data = journal_balance(Journal.search([('type', '=', 'bank')]))

        # ── Recent Invoices ───────────────────────────────────────────────
        recent_invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ], order='invoice_date desc, id desc', limit=10)

        invoice_summary = []
        for inv in recent_invoices:
            invoice_summary.append({
                'id':            inv.id,
                'name':          inv.name,
                'partner':       inv.partner_id.name,
                'date':          inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '-',
                'amount_total':  round(inv.amount_total, 3),
                'amount_due':    round(inv.amount_residual, 3),
                'payment_state': inv.payment_state,
                'payment_label': dict(inv._fields['payment_state'].selection).get(inv.payment_state, ''),
            })

        # ── Outstanding Invoices ──────────────────────────────────────────
        outstanding_list_recs = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ], order='invoice_date asc', limit=10)

        outstanding_data = []
        for inv in outstanding_list_recs:
            days_overdue = (today - inv.invoice_date).days if inv.invoice_date else 0
            outstanding_data.append({
                'id':            inv.id,
                'name':          inv.name,
                'partner':       inv.partner_id.name,
                'date':          inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '-',
                'amount_total':  round(inv.amount_total, 3),
                'amount_due':    round(inv.amount_residual, 3),
                'days_overdue':  days_overdue,
                'payment_state': inv.payment_state,
            })

        # ── Department Revenue ────────────────────────────────────────────
        dept_revenue = {}
        for inv in month_invoices:
            for line in inv.invoice_line_ids:
                categ = (
                    line.product_id.categ_id.name
                    if line.product_id and line.product_id.categ_id
                    else 'Other'
                )
                dept_revenue[categ] = dept_revenue.get(categ, 0) + line.price_subtotal

        dept_chart = [
            {'label': k, 'value': round(v, 3)}
            for k, v in sorted(dept_revenue.items(), key=lambda x: -x[1])
        ]

        return {
            'kpis': {
                'revenue_today':      round(revenue_today, 3),
                'revenue_this_month': round(revenue_this_month, 3),
                'revenue_paid_month': round(revenue_paid_month, 3),
                'outstanding_amount': round(outstanding_amount, 3),
                'outstanding_count':  outstanding_count,
                'total_patients':     total_patients,
                'patients_month':     patients_month,
                'appointments_today': appointments_today,
                'appointments_month': appointments_month,
                'lab_requests_today': lab_requests_today,
                'lab_requests_month': lab_requests_month,
            },
            'revenue_chart':    revenue_chart,
            'dept_chart':       dept_chart,
            'cash_data':        cash_data,
            'bank_data':        bank_data,
            'invoice_summary':  invoice_summary,
            'outstanding_list': outstanding_data,
        }