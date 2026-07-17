def check_schema(env):
    """Fail-closed (ADR-002): schema cerută trebuie să existe la instalare."""
    Leave = env["hr.leave"]
    for field in ("employee_id", "date_from", "date_to", "state"):
        if field not in Leave._fields:
            raise RuntimeError(
                f"pmorg_anchor_time_off: schemă incompatibilă — hr.leave.{field} lipsă."
            )
