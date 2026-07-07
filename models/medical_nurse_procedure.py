from odoo import models, fields, api


class MedicalNurseProcedure(models.Model):
    """
    Nurse procedures performed during an appointment.
    Each line is one procedure with a product, quantity, and price.
    These lines feed directly into the appointment invoice.
    """
    _name = 'medical.nurse.procedure'
    _description = 'Nurse Procedure'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)

    appointment_id = fields.Many2one(
        'medical.appointment',
        string='Appointment',
        required=True,
        ondelete='cascade'
    )
    patient_id = fields.Many2one(
        related='appointment_id.patient_id',
        string='Patient',
        store=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Procedure',
        domain=[('type', '=', 'service')],
        required=True
    )
    description = fields.Char(
        string='Description / Notes',
        compute='_compute_description',
        store=True, readonly=False
    )
    quantity  = fields.Float(string='Qty',        default=1.0)
    unit_price = fields.Float(
        string='Unit Price',
        compute='_compute_unit_price',
        store=True, readonly=False
    )
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True
    )

    @api.depends('product_id')
    def _compute_description(self):
        for rec in self:
            rec.description = rec.product_id.name if rec.product_id else ''

    @api.depends('product_id')
    def _compute_unit_price(self):
        for rec in self:
            rec.unit_price = rec.product_id.lst_price if rec.product_id else 0.0

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_price