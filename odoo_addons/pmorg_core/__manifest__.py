{
    "name": "PMORG Core",
    "version": "19.0.1.1.0",
    "summary": "Operator organizațional persistent — nucleu",
    "description": "PMORG Core — aplicația PMORG transformă Odoo într-un operator organizațional persistent.",
    "author": "PMORG",
    "category": "Project",
    "license": "LGPL-3",
    "depends": ["project", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "views/pmorg_initiative_views.xml",
        "views/project_task_views.xml",
        "views/pmorg_menu.xml",
        "data/pmorg_data.xml",
    ],
    "demo": [
        "data/pmorg_demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
