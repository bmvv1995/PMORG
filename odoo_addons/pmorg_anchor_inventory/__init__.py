def check_schema(env):
    """Fail-closed (ADR-002): relația move part_of transfer trebuie să existe."""
    Move = env["stock.move"]
    if "picking_id" not in Move._fields:
        raise RuntimeError(
            "pmorg_anchor_inventory: schemă incompatibilă — stock.move.picking_id lipsă."
        )
