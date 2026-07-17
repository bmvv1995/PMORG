{
    "name": "PMORG Anchor Pack — Time Off",
    "version": "19.0.1.0.0",
    "summary": "Vocabular de ancorare Time Off (LEAVE_REQUEST)",
    "author": "PMORG",
    "category": "Project",
    "license": "LGPL-3",
    "depends": ["pmorg_core", "hr_holidays"],
    "data": ["data/anchor_types.xml"],
    "post_init_hook": "check_schema",
    "installable": True,
    "auto_install": False,
}
