# -*- coding: utf-8 -*-
{
    'name': 'Ekram Medical Center',
    # 'version': '18.0.1.1.0',
    'version': '19.0.1.1.0',
    'category': 'Healthcare',
    'summary': 'Ekram Medical Center Management System - Laboratory, Appointments, Consultations',
    'description': """
Ekram Medical Center Management System
=======================================
Version 1.1 MVP

Features:
- Patient Registration (extends res.partner)
- Appointment Management
- Doctor Consultation
- Laboratory Information System
- Professional Lab Reports
- Accounting Integration (account.move, account.payment)
- Role-based Security (Reception, Doctor, Lab Technician, Admin)
- Operational Dashboards
- Demo Data
    """,
    'author': 'Abdulla Bashir',
    'website': 'https://www.3bdalla3adil.github.io',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'product',
        'account',
        'sale_management',
        'web',
    ],
    'data': [
        'security/ekram_medical_groups.xml',
        'security/ir.model.access.csv',
        'security/ekram_medical_record_rules.xml',
        'data/ekram_medical_sequence.xml',
        'data/ekram_medical_product_category.xml',
        'views/res_partner_views.xml',
        'views/medical_appointment_views.xml',
        'views/medical_consultation_views.xml',
        'views/medical_lab_template_views.xml',
        'views/medical_lab_request_views.xml',
        'views/medical_lab_result_views.xml',
        'views/medical_dashboard_views.xml',
        'views/medical_dashboard_actions.xml',
        'reports/medical_lab_report.xml',
        'reports/medical_lab_report_template.xml',
        'views/ekram_medical_menus.xml',
    ],
    'demo': [
        'demo/ekram_medical_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'ekram_medical/static/src/css/ekram_medical.css',
            # 'ekram_medical/static/src/js/medical_dashboard.js',
            # 'ekram_medical/static/src/xml/medical_dashboard.xml',
            'ekram_medical/static/src/css/ekram_dashboard.css',
            'ekram_medical/static/src/xml/reception_dashboard.xml',
            # 'ekram_medical/static/src/xml/doctor_dashboard.xml',
            # 'ekram_medical/static/src/xml/lab_dashboard.xml',
            'ekram_medical/static/src/js/reception_dashboard.js',
            # 'ekram_medical/static/src/js/doctor_dashboard.js',
            # 'ekram_medical/static/src/js/lab_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}