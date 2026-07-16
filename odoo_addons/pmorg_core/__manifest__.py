{
    "name": "PMORG Core",
    "version": "19.0.1.2.0",
    "summary": "Operator organizațional persistent — nucleu",
    "description": "PMORG Core — aplicația PMORG transformă Odoo într-un operator organizațional persistent. Nucleu agnostic de domeniu (ADR-013): fără dependențe de HR, Inventory sau Time Off.",
    "author": "PMORG",
    "category": "Project",
    "license": "LGPL-3",
    "depends": ["base", "project"],
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
