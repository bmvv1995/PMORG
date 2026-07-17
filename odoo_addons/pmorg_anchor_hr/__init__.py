def check_schema(env):
    """Fail-closed (ADR-002): schema cerută trebuie să existe la instalare."""
    Employee = env["hr.employee"]
    for field in ("parent_id", "work_contact_id", "department_id"):
        if field not in Employee._fields:
            raise RuntimeError(
                f"pmorg_anchor_hr: schemă incompatibilă — hr.employee.{field} lipsă."
            )
