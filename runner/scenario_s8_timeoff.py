#!/usr/bin/env python3
"""Gate D — S8: anchor pack Time Off, replanificare la absență sintetică."""

import sys
import uuid

from pmorg_runner.client import OdooApiClient
from pmorg_runner.memory_client import MemoryClient

RUN = uuid.uuid4().hex[:8]
CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not cond else ""))


def main():
    api = OdooApiClient("http://127.0.0.1:18070", "pmorg_srv", "admin",
                        "admin", actor_id="harness-s8")
    mem = MemoryClient("http://127.0.0.1:18092")
    mem_min = MemoryClient("http://127.0.0.1:18091")
    NOW = "2026-07-10 09:00:00"

    company = api.execute("res.company", "search",
                          [["name", "=", "Birou Servicii Test SRL"]],
                          limit=1)[0]
    api.execute("res.users", "write", [api.uid],
                {"company_ids": [(4, company)]})
    dan = api.execute("hr.employee", "search",
                      [["name", "=", "Dan Petre"]], limit=1)[0]

    ltype = api.execute("hr.leave.type", "create", {
        "name": f"Concediu TEST {RUN}", "requires_allocation": False,
        "company_id": company,
    })
    leave = api.execute("hr.leave", "create", {
        "holiday_status_id": ltype, "employee_id": dan,
        "request_date_from": "2026-07-20", "request_date_to": "2026-07-24",
    })
    st = api.execute("hr.leave", "read", [leave], ["state"])[0]
    check("S8: absența sintetică există (hr.leave real)",
          st["state"] in ("draft", "confirm", "validate"))

    init = api.execute("pmorg.initiative", "search", [], limit=1)[0]
    task = api.call("propose_task", {
        "initiative_id": init, "name": f"GD-S8 livrabil {RUN}",
        "pmorg_task_type": "execution", "execution_mode": "agent",
    }, NOW)["result"]["task_id"]
    api.execute("project.task", "write", [task],
                {"date_deadline": "2026-07-22"})  # în mijlocul absenței

    # controllerul detectează suprapunerea determinist și replanifică
    overlap = api.execute("hr.leave", "search_count", [
        ["employee_id", "=", dan],
        ["request_date_from", "<=", "2026-07-22"],
        ["request_date_to", ">=", "2026-07-22"],
    ])
    check("S8: suprapunerea termen-absență e detectabilă determinist",
          overlap == 1)

    claim = api.call("claim_task", {"task_id": task, "now": NOW}, NOW)["result"]
    ref = {"task_id": task, "run_id": claim["run_id"],
           "lease_token": claim["lease_token"]}
    ok = api.call("schedule_next_check",
                  dict(ref, next_check_at="2026-07-27 09:00:00",
                       reason="replanificat: responsabilul e în concediu",
                       now=NOW), NOW)
    check("S8: replanificarea după absență e aplicată",
          ok["status"] == "ok")
    state = api.execute("project.task", "read", [task], ["next_check_at"])[0]
    check("S8: next_check_at sare peste fereastra absenței",
          str(state["next_check_at"]) > "2026-07-24")

    ev = mem.ok("memory_capture_evidence", external_id=f"gd-s8-{RUN}",
                source="gd", author_ref="gd:controller",
                content="Replanificat: Dan e în concediu 20-24 iulie.")
    cl = mem.ok("memory_propose_claim",
                statement="GD-S8: livrabil replanificat din cauza absenței",
                author_ref="gd:controller", evidence_ids=[ev["evidence_id"]],
                anchors=[
                    {"anchor_type": "LEAVE_REQUEST", "model": "hr.leave",
                     "res_id": leave, "role": "subject"},
                    {"anchor_type": "TASK", "model": "project.task",
                     "res_id": task, "role": "mentions"},
                ])
    check("S8: claim ancorat la absența reală (LEAVE_REQUEST)",
          cl["status"] == "candidate")
    check("S8: profilul minimal REFUZĂ ancora de concediu (fail-closed)",
          mem_min.expect_error("memory_propose_claim",
                               "MEM_ANCHOR_TYPE_UNKNOWN",
                               statement="x", author_ref="gd:x",
                               evidence_ids=[1],
                               anchors=[{"anchor_type": "LEAVE_REQUEST",
                                         "model": "hr.leave",
                                         "res_id": leave}]))

    failed = CHECKS.count(False)
    print(f"===== S8: {len(CHECKS)} verificări, {failed} eșuate =====")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
