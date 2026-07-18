{
    "name": "PMORG Anchor Pack — HR",
    "version": "19.0.1.0.0",
    "summary": "Vocabular de ancorare Employees (EMPLOYEE, DEPARTMENT)",
    "author": "PMORG",
    "category": "Project",
    "license": "LGPL-3",
    "depends": ["pmorg_core", "hr"],
    "data": ["data/anchor_types.xml"],
    "post_init_hook": "check_schema",
    "installable": True,
    "auto_install": False,
}
