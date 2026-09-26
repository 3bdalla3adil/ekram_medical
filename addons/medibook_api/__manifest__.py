{
    "name": "MediBook API",
    "version": "19.0.3.0.0",
    "category": "Healthcare",
    "summary": "Firebase-authenticated MediBook API backend for Odoo 19",
    "depends": [
        "base",
        "mail"
    ],
    "external_dependencies": {
        "python": [
            "jwt",
            "requests"
        ]
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/config.xml",
        "views/medibook_views.xml"
    ],
    "installable": true,
    "application": true,
    "license": "LGPL-3"
}
