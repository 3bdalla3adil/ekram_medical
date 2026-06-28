# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MedicalLabRequest(models.Model):
    _name = 'medical.lab.request'
    _description = 'Laboratory Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Request Reference',
        required=True,
        copy=False,
        readonly=True,
        default='/',
        index=True,
    )
    patient_id = fields.Many2one(
        'res.partner',
        string='Patient',
        required=True,
        domain=[('is_patient', '=', True)],
        tracking=True,
        index=True,
    )
    doctor_id = fields.Many2one(
        'hr.employee',
        string='Requesting Doctor',
        tracking=True,
    )
    consultation_id = fields.Many2one(
        'medical.consultation',
        string='Consultation',
        tracking=True,
    )
    request_date = fields.Datetime(
        string='Request Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Critical'),
    ], string='Priority', default='0')
    template_ids = fields.Many2many(
        'medical.lab.template',
        string='Requested Investigations',
    )
    result_ids = fields.One2many(
        'medical.lab.result',
        'request_id',
        string='Results',
    )
    result_count = fields.Integer(
        string='Results',
        compute='_compute_result_count',
    )
    notes = fields.Text(string='Clinical Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )

    # ── Compute ───────────────────────────────────────────────────────────────
    def _compute_result_count(self):
        for rec in self:
            rec.result_count = len(rec.result_ids)

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'medical.lab.request'
                ) or '/'
        return super().create(vals_list)

    # ── Workflow ──────────────────────────────────────────────────────────────
    def action_process(self):
        for rec in self:
            rec.state = 'processing'
            # Auto-create result records for each template
            for template in rec.template_ids:
                existing = self.env['medical.lab.result'].search([
                    ('request_id', '=', rec.id),
                    ('template_id', '=', template.id),
                ])
                if not existing:
                    result = self.env['medical.lab.result'].create({
                        'request_id': rec.id,
                        'patient_id': rec.patient_id.id,
                        'template_id': template.id,
                        'doctor_id': rec.doctor_id.id,
                    })
                    result._load_template_lines()

    def action_complete(self):
        for rec in self:
            rec.state = 'completed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_view_results(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Results',
            'res_model': 'medical.lab.result',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            'ekram_medical.action_report_lab_result'
        ).report_action(self)