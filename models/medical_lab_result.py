# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MedicalLabResult(models.Model):
    _name = 'medical.lab.result'
    _description = 'Laboratory Result'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Result Reference',
        compute='_compute_name',
        store=True,
    )
    request_id = fields.Many2one(
        'medical.lab.request',
        string='Lab Request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    patient_id = fields.Many2one(
        'res.partner',
        string='Patient',
        required=True,
        domain=[('is_patient', '=', True)],
        index=True,
    )
    template_id = fields.Many2one(
        'medical.lab.template',
        string='Investigation',
        required=True,
        tracking=True,
    )
    doctor_id = fields.Many2one(
        'hr.employee',
        string='Requesting Doctor',
    )
    technician_id = fields.Many2one(
        'hr.employee',
        string='Lab Technician',
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        ),
    )
    result_date = fields.Datetime(
        string='Result Date',
        default=fields.Datetime.now,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    line_ids = fields.One2many(
        'medical.lab.result.line',
        'result_id',
        string='Result Lines',
    )
    remarks = fields.Text(string='General Remarks')
    validated_by = fields.Many2one(
        'res.users',
        string='Validated By',
        readonly=True,
    )
    validated_date = fields.Datetime(
        string='Validated Date',
        readonly=True,
    )

    # ── Compute ───────────────────────────────────────────────────────────────
    @api.depends('request_id', 'template_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.request_id:
                parts.append(rec.request_id.name)
            if rec.template_id:
                parts.append(rec.template_id.name)
            rec.name = ' / '.join(parts) if parts else '/'

    # ── Template Loading ──────────────────────────────────────────────────────
    def _load_template_lines(self):
        """Load result lines from the selected template."""
        for rec in self:
            if not rec.template_id:
                continue
            # Remove existing lines
            rec.line_ids.unlink()
            lines = []
            for tl in rec.template_id.line_ids:
                lines.append({
                    'result_id': rec.id,
                    'sequence': tl.sequence,
                    'test_name': tl.test_name,
                    'unit': tl.unit,
                    'normal_range_text': tl.normal_range_text,
                    'normal_min': tl.normal_min,
                    'normal_max': tl.normal_max,
                    'result_type': tl.result_type,
                })
            self.env['medical.lab.result.line'].create(lines)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self._load_template_lines()

    # ── Workflow ──────────────────────────────────────────────────────────────
    def action_validate(self):
        for rec in self:
            rec.state = 'validated'
            rec.validated_by = self.env.uid
            rec.validated_date = fields.Datetime.now()
            # Mark request as completed if all results validated
            if rec.request_id:
                all_results = rec.request_id.result_ids
                if all(r.state == 'validated' for r in all_results):
                    rec.request_id.state = 'completed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.validated_by = False
            rec.validated_date = False

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            'ekram_medical.action_report_lab_result'
        ).report_action(self.request_id)


class MedicalLabResultLine(models.Model):
    _name = 'medical.lab.result.line'
    _description = 'Laboratory Result Line'
    _order = 'sequence, id'

    result_id = fields.Many2one(
        'medical.lab.result',
        string='Result',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    test_name = fields.Char(string='Test Name', required=True, readonly=True)
    result_value = fields.Char(string='Result')
    result_numeric = fields.Float(
        string='Numeric Result',
        digits=(10, 3),
        compute='_compute_result_numeric',
        store=True,
    )
    unit = fields.Char(string='Unit', readonly=True)
    normal_range_text = fields.Char(string='Reference Range', readonly=True)
    normal_min = fields.Float(string='Normal Min', digits=(10, 3), readonly=True)
    normal_max = fields.Float(string='Normal Max', digits=(10, 3), readonly=True)
    result_type = fields.Selection([
        ('numeric', 'Numeric'),
        ('text', 'Text'),
        ('positive_negative', 'Positive/Negative'),
    ], string='Result Type', default='numeric', readonly=True)
    flag = fields.Selection([
        ('normal', 'Normal'),
        ('high', 'High'),
        ('low', 'Low'),
        ('critical', 'Critical'),
    ], string='Flag', compute='_compute_flag', store=True)
    remarks = fields.Char(string='Remarks')

    # ── Compute ───────────────────────────────────────────────────────────────
    @api.depends('result_value')
    def _compute_result_numeric(self):
        for rec in self:
            try:
                rec.result_numeric = float(rec.result_value or 0)
            except (ValueError, TypeError):
                rec.result_numeric = 0.0

    @api.depends('result_numeric', 'normal_min', 'normal_max', 'result_type', 'result_value')
    def _compute_flag(self):
        for rec in self:
            if rec.result_type != 'numeric' or not rec.result_value:
                rec.flag = 'normal'
                continue
            try:
                val = float(rec.result_value)
            except (ValueError, TypeError):
                rec.flag = 'normal'
                continue
            if rec.normal_min and rec.normal_max:
                if val < rec.normal_min:
                    # Critical if more than 20% below min
                    if val < rec.normal_min * 0.8:
                        rec.flag = 'critical'
                    else:
                        rec.flag = 'low'
                elif val > rec.normal_max:
                    # Critical if more than 20% above max
                    if val > rec.normal_max * 1.2:
                        rec.flag = 'critical'
                    else:
                        rec.flag = 'high'
                else:
                    rec.flag = 'normal'
            else:
                rec.flag = 'normal'