# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MedicalLabTemplate(models.Model):
    _name = 'medical.lab.template'
    _description = 'Laboratory Investigation Template'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Investigation Name', required=True, index=True)
    code = fields.Char(string='Code', index=True)
    product_id = fields.Many2one(
        'product.template',
        string='Investigation Product',
        domain=[('type', '=', 'service')],
        help='Link to product for invoicing. Price is taken from the product.',
    )
    department = fields.Selection([
        ('hematology', 'Hematology'),
        ('biochemistry', 'Biochemistry'),
        ('microbiology', 'Microbiology'),
        ('immunology', 'Immunology'),
        ('urine', 'Urine Analysis'),
        ('hormones', 'Hormones'),
        ('other', 'Other'),
    ], string='Department', default='other')
    sample_type = fields.Selection([
        ('blood', 'Blood'),
        ('urine', 'Urine'),
        ('stool', 'Stool'),
        ('swab', 'Swab'),
        ('other', 'Other'),
    ], string='Sample Type', default='blood')
    turnaround_hours = fields.Integer(string='Turnaround (Hours)', default=24)
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
    line_ids = fields.One2many(
        'medical.lab.template.line',
        'template_id',
        string='Parameters',
        copy=True,
    )
    line_count = fields.Integer(
        string='Parameters',
        compute='_compute_line_count',
    )

    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_view_template_lines(self):
        pass


class MedicalLabTemplateLine(models.Model):
    _name = 'medical.lab.template.line'
    _description = 'Laboratory Template Parameter'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'medical.lab.template',
        string='Template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    test_name = fields.Char(string='Test Name', required=True)
    unit = fields.Char(string='Unit')
    normal_range_text = fields.Char(string='Normal Range')
    normal_min = fields.Float(string='Normal Min', digits=(10, 3))
    normal_max = fields.Float(string='Normal Max', digits=(10, 3))
    normal_min_female = fields.Float(string='Normal Min (Female)', digits=(10, 3))
    normal_max_female = fields.Float(string='Normal Max (Female)', digits=(10, 3))
    result_type = fields.Selection([
        ('numeric', 'Numeric'),
        ('text', 'Text'),
        ('positive_negative', 'Positive/Negative'),
    ], string='Result Type', default='numeric')
    notes = fields.Char(string='Notes')