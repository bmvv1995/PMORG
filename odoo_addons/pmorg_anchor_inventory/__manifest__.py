{
    "name": "PMORG Anchor Pack — Inventory",
    "version": "19.0.1.0.0",
    "summary": "Vocabular de ancorare Inventory (INVENTORY_TRANSFER, INVENTORY_MOVE)",
    "author": "PMORG",
    "category": "Project",
    "license": "LGPL-3",
    "depends": ["pmorg_core", "stock"],
    "data": ["data/anchor_types.xml"],
    "post_init_hook": "check_schema",
    "installable": True,
    "auto_install": False,
}
