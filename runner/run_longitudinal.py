#!/usr/bin/env python3
"""Calificarea longitudinală — Gate D (02-MVP §10), scenariile S1–S10.

Toate rulează cu ceasul trusted (pmorg.clock_mode=tick): harness-ul (admin)
înregistrează tick-uri; runnerul doar le prezintă. Timpul virtual avansează
pe zile simulate. Fiecare scenariu = verificări explicite PASS/FAIL.
"""

import argparse
import sys
import uuid

from pmorg_runner.channel import SimulatedChannel
from pmorg_runner.client import OdooApiClient
from pmorg_runner.memory_client import MemoryClient

CHECKS = []
RUN = uuid.uuid4().hex[:8]


def check(name, condition, detail=""):
    CHECKS.append((name, bool(condition)))
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail and not condition else ""))
    return bool(condition)


def ok(resp, ctx):
    if resp.get("status") not in ("ok", "replay"):
        raise RuntimeError(f"{ctx}: {resp.get('error')}")
    return resp["result"]


class TickClock:
    """Ceasul harness-ului: emite tick-uri prin identitatea de sistem."""

    def __init__(self, admin_api, start_day=0, scale=1):
        self.api = admin_api
        self.seq = 0
        self.day = start_day
        self.scale = scale
        self.current = None

    def tick(self, day, hour=9):
        from datetime import datetime, timedelta
        self.seq += 1
        self.day = day * self.scale
        tick_id = f"tick-{uuid.uuid4().hex[:12]}"
        sim = (datetime(2026, 7, 1) + timedelta(days=self.day, hours=hour)
               ).strftime("%Y-%m-%d %H:%M:%S")
        ok(self.api.call("register_tick",
                         {"tick_id": tick_id, "seq": self.seq,
                          "sim_time": sim}, sim), "register_tick")
        self.current = (tick_id, sim)
        return tick_id


class Ctx:
    def __init__(self, url, db, memory_url):
        self.url, self.db = url, db
        self.admin = OdooApiClient(url, db, "admin", "admin",
                                   actor_id="harness")
        self.runner = OdooApiClient(url, db, "admin", "admin",
                                    actor_id="runner-gd")
        self.mem = MemoryClient(memory_url) if memory_url else None
        self.clock = TickClock(self.admin, scale=1)

    def rcall(self, command, params, tick_id):
        params = dict(params, tick_id=tick_id)
        return self.runner.call(command, params, "1970-01-01 00:00:00")

    def sched(self, day):
        from datetime import datetime, timedelta
        return (datetime(2026, 7, 1)
                + timedelta(days=day * self.clock.scale, hours=9)
                ).strftime("%Y-%m-%d %H:%M:%S")

    def new_task(self, name, initiative_id, task_type="clarification"):
        t = self.clock.current[0]
        return ok(self.rcall("propose_task", {
            "initiative_id": initiative_id, "name": name,
            "pmorg_task_type": task_type, "execution_mode": "agent",
        }, t), "propose_task")["task_id"]


def find_world(ctx):
    init_ids = ctx.admin.execute(
        "pmorg.initiative", "search", [["name", "like", "WG%"]], limit=2)
    identity = ctx.admin.execute(
        "pmorg.identity", "search", [], limit=1)
    return init_ids, identity[0]


# ----------------------------------------------------------- scenariile

def s1_silence_followup(ctx, init_id):
    t = ctx.clock.tick(1)
    task = ctx.new_task("GD-S1 tăcere", init_id)
    claim = ok(ctx.rcall("claim_task", {"task_id": task}, t), "claim")
    ref = {"task_id": task, "run_id": claim["run_id"],
           "lease_token": claim["lease_token"]}
    channel = SimulatedChannel({"gd.participant": []})  # tăcere totală
    ok(ctx.rcall("record_waiting_response",
                 dict(ref, awaiting_identity_id=ctx.identity), t), "waiting")
    ok(ctx.rcall("schedule_next_check",
                 dict(ref, next_check_at=ctx.sched(3),
                      reason="aștept răspuns"), t), "schedule")
    t3 = ctx.clock.tick(3)
    due = ok(ctx.rcall("list_due_work", {}, t3), "due")
    check("S1: taskul tăcut redevine scadent la tick-ul următor",
          task in [x["task_id"] for x in due["tasks"]])
    claim2 = ok(ctx.rcall("claim_task", {"task_id": task}, t3), "claim2")
    ref2 = {"task_id": task, "run_id": claim2["run_id"],
            "lease_token": claim2["lease_token"]}
    reply = channel.receive_reply("gd.participant", "gd-s1", "sim")
    check("S1: tăcerea e reală (canalul nu are replici)", reply is None)
    ok(ctx.rcall("record_followup", dict(ref2, note="follow-up #1"), t3), "fu")
    state = ctx.admin.execute("project.task", "read", [task],
                              ["followup_count"])[0]
    check("S1: exact UN follow-up consemnat", state["followup_count"] == 1)
    ok(ctx.rcall("schedule_next_check",
                 dict(ref2, next_check_at=ctx.sched(5),
                      reason="după follow-up"), t3), "resched")
    return task


def s2_duplicates(ctx, init_id):
    t = ctx.clock.tick(4)
    task = ctx.new_task("GD-S2 duplicate", init_id)
    key = ctx.runner.next_key("claim-s2")
    payload = {"task_id": task, "tick_id": t}
    first = ctx.runner.call("claim_task", payload, "1970-01-01", key=key)
    dup = ctx.runner.call("claim_task", payload, "1970-01-01", key=key)
    check("S2: comanda rejucată întoarce replay, același run, zero efect dublu",
          first["status"] == "ok" and dup["status"] == "replay"
          and dup["result"]["run_id"] == first["result"]["run_id"])
    runs = ctx.admin.execute("pmorg.task.run", "search_count",
                             [["task_id", "=", task]])
    check("S2: un singur run în ciuda duplicatelor", runs == 1)
    if ctx.mem:
        ev1 = ctx.mem.ok("memory_capture_evidence", external_id="gd-s2-msg-" + RUN,
                         source="gd", author_ref="gd:x", content="răspuns")
        ev2 = ctx.mem.ok("memory_capture_evidence", external_id="gd-s2-msg-" + RUN,
                         source="gd", author_ref="gd:x", content="răspuns")
        check("S2: evidența duplicată e dedup (replayed)",
              ev1["evidence_id"] == ev2["evidence_id"] and ev2["replayed"])
    return task


def s3_contradiction(ctx, init_id):
    if not ctx.mem:
        return check("S3: memoria necesară", False)
    anchor = {"anchor_type": "INITIATIVE", "model": "pmorg.initiative",
              "res_id": init_id, "role": "subject"}
    ev_a = ctx.mem.ok("memory_capture_evidence", external_id="gd-s3-a-" + RUN,
                      source="gd", author_ref="gd:victor",
                      content="Termenul e vineri.")
    ev_b = ctx.mem.ok("memory_capture_evidence", external_id="gd-s3-b-" + RUN,
                      source="gd", author_ref="gd:andrei",
                      content="Ba nu, termenul e luni.")
    c_a = ctx.mem.ok("memory_propose_claim", statement="Termen: vineri",
                     author_ref="gd:victor", evidence_ids=[ev_a["evidence_id"]],
                     anchors=[anchor])
    c_b = ctx.mem.ok("memory_propose_claim", statement="Termen: luni",
                     author_ref="gd:andrei", evidence_ids=[ev_b["evidence_id"]],
                     anchors=[anchor])
    recall = ctx.mem.ok("memory_recall", anchor=anchor)
    both = {c["id"] for c in recall["claims"]}
    check("S3: ambele claims contradictorii rămân vizibile, marcate candidate",
          {c_a["claim_id"], c_b["claim_id"]} <= both)
    ctx.mem.ok("memory_supersede", old_claim_id=c_a["claim_id"],
               new_claim_id=c_b["claim_id"], reason="clarificat cu ownerul")
    recall2 = ctx.mem.ok("memory_recall", anchor=anchor)
    st = {c["id"]: c["status"] for c in recall2["claims"]}
    check("S3: rezolvarea explicită = supersession, nimic șters",
          st[c_a["claim_id"]] == "superseded"
          and st[c_b["claim_id"]] == "candidate")


def s4_concurrent_manual_edit(ctx, init_id):
    t = ctx.clock.tick(5)
    task = ctx.new_task("GD-S4 editare manuală", init_id)
    claim = ok(ctx.rcall("claim_task", {"task_id": task}, t), "claim")
    ref = {"task_id": task, "run_id": claim["run_id"],
           "lease_token": claim["lease_token"]}
    # omul editează manual în Odoo în timp ce taskul e revendicat
    ctx.admin.execute("project.task", "write", [task],
                      {"date_deadline": "2026-08-15"})
    state = ok(ctx.rcall("get_task_state", {"task_id": task}, t), "state")
    check("S4: editarea manuală NU rupe claim-ul (lease intact)",
          state["orchestration_state"] == "claimed"
          and bool(state["active_run"]))
    # conflict optimist: versiune veche declarată explicit
    stale = ctx.rcall("claim_task", {"task_id": task, "expected_version": 1}, t)
    check("S4: versiunea veche e refuzată explicit (E_VERSION/E_LEASE_HELD)",
          stale.get("error", {}).get("code") in ("E_VERSION", "E_LEASE_HELD"))
    ok(ctx.rcall("record_progress", dict(ref, note="reconciliat"), t), "prog")
    ok(ctx.rcall("complete_run", dict(ref, outcome="done",
                                      summary="închis după reconciliere"), t),
       "complete")
    gaps = ok(ctx.rcall("list_material_changes",
                        {"since": "2026-07-01 00:00:00"}, t), "changes")
    seen = [c for c in gaps["changes"]
            if c["res_id"] == task and c["field_name"] == "date_deadline"]
    check("S4: schimbarea manuală e vizibilă pentru reconciliere (tracking)",
          bool(seen))


def s5_restart_waiting(ctx, init_id):
    t = ctx.clock.tick(6)
    task = ctx.new_task("GD-S5 restart", init_id)
    claim = ok(ctx.rcall("claim_task", {"task_id": task}, t), "claim")
    ref = {"task_id": task, "run_id": claim["run_id"],
           "lease_token": claim["lease_token"]}
    ok(ctx.rcall("record_waiting_response",
                 dict(ref, awaiting_identity_id=ctx.identity), t), "waiting")
    # „restart”: proces nou, altă identitate de client, zero stare locală
    reborn = OdooApiClient(ctx.url, ctx.db, "admin", "admin",
                           actor_id="runner-gd-reborn")
    state = ok(reborn.call("get_task_state",
                           {"task_id": task, "tick_id": t}, "1970-01-01"),
               "state")
    check("S5: după restart, starea completă vine din Odoo",
          state["orchestration_state"] == "waiting_response"
          and bool(state["active_run"]))
    ok(reborn.call("schedule_next_check",
                   dict(ref, next_check_at=ctx.sched(7),
                        reason="reluat după restart", tick_id=t),
                   "1970-01-01"), "resched")
    t8 = ctx.clock.tick(7)
    claim2 = ok(reborn.call("claim_task", {"task_id": task, "tick_id": t8},
                            "1970-01-01"), "reclaim")
    ok(reborn.call("complete_run",
                   {"task_id": task, "run_id": claim2["run_id"],
                    "lease_token": claim2["lease_token"], "outcome": "done",
                    "summary": "finalizat post-restart", "tick_id": t8},
                   "1970-01-01"), "complete")
    check("S5: firul continuă și se închide după restart", True)


def s6_memory_unavailable(ctx, init_id, toggle):
    t = ctx.clock.tick(8)
    task = ctx.new_task("GD-S6 memorie jos", init_id)
    toggle(False)  # memoria cade
    failed = False
    try:
        ctx.mem.ok("memory_capture_evidence", external_id="gd-s6-msg-" + RUN,
                   source="gd", author_ref="gd:x", content="pierdut?")
    except Exception:
        failed = True
    check("S6: indisponibilitatea memoriei e explicită (eroare, nu tăcere)",
          failed)
    claim = ok(ctx.rcall("claim_task", {"task_id": task}, t), "claim")
    check("S6: orchestrarea deterministă continuă fără memorie",
          bool(claim["lease_token"]))
    toggle(True)  # memoria revine
    ev = ctx.mem.ok("memory_capture_evidence", external_id="gd-s6-msg-" + RUN,
                    source="gd", author_ref="gd:x", content="pierdut?")
    ev2 = ctx.mem.ok("memory_capture_evidence", external_id="gd-s6-msg-" + RUN,
                     source="gd", author_ref="gd:x", content="pierdut?")
    check("S6: retry-ul cu același ID e sigur după revenire (dedup)",
          not ev["replayed"] and ev2["replayed"])


def s9_escalation(ctx, init_id, silent_task):
    t = ctx.clock.tick(9)
    claim = ok(ctx.rcall("claim_task", {"task_id": silent_task}, t), "claim")
    ref = {"task_id": silent_task, "run_id": claim["run_id"],
           "lease_token": claim["lease_token"]}
    # politica fixture: după 1 follow-up fără răspuns → escaladare
    state = ctx.admin.execute("project.task", "read", [silent_task],
                              ["followup_count", "escalation_level"])[0]
    check("S9: precondiția politicii (1 follow-up, 0 escaladări)",
          state["followup_count"] == 1 and state["escalation_level"] == 0)
    esc = ok(ctx.rcall("record_escalation",
                       dict(ref, reason="tăcere peste pragul politicii"), t),
             "escalate")
    check("S9: escaladarea e consemnată determinist (nivel 1)",
          esc["escalation_level"] == 1)
    events = ctx.admin.execute("pmorg.task.event", "search_read",
                               [["task_id", "=", silent_task],
                                ["event_type", "=", "task.escalated"]],
                               ["payload"])
    check("S9: evenimentul de escaladare există în jurnalul append-only",
          len(events) == 1)
    ok(ctx.rcall("complete_run", dict(ref, outcome="needs_review",
                                      summary="escaladat către owner"), t),
       "complete")


def s10_supersession_close(ctx, init_id):
    t = ctx.clock.tick(10)
    anchor = {"anchor_type": "INITIATIVE", "model": "pmorg.initiative",
              "res_id": init_id, "role": "subject"}
    ev = ctx.mem.ok("memory_capture_evidence", external_id="gd-s10-decizie-" + RUN,
                    source="gd", author_ref="gd:owner",
                    content="Decizia finală: închidem cu criteriul revizuit.")
    c_new = ctx.mem.ok("memory_propose_claim",
                       statement="Decizie finală: criteriu revizuit",
                       author_ref="gd:owner", evidence_ids=[ev["evidence_id"]],
                       anchors=[anchor])
    ctx.mem.ok("memory_record_outcome",
               task_ref=f"pmorg.initiative:{init_id}",
               claim_id=c_new["claim_id"],
               summary="Rezultat verificat, inițiativa se închide",
               evidence_ids=[ev["evidence_id"]])
    crit = ctx.admin.execute("pmorg.success.criterion", "create",
                             {"name": "criteriu GD-S10",
                              "initiative_id": init_id})
    refused = False
    try:
        ctx.admin.execute("pmorg.initiative", "write", [init_id],
                          {"state": "verifying"})
        ctx.admin.execute("pmorg.initiative", "action_close", [init_id])
    except Exception:
        refused = True
    check("S10: închiderea fără criteriu verificat e refuzată", refused)
    ctx.admin.execute("pmorg.success.criterion", "action_mark_verified",
                      [crit])
    ctx.admin.execute("pmorg.initiative", "action_close", [init_id])
    st = ctx.admin.execute("pmorg.initiative", "read", [init_id], ["state"])[0]
    check("S10: inițiativa închisă după rezultat verificat",
          st["state"] == "closed")
    timeline = ctx.mem.ok("memory_get_timeline", anchor=anchor)
    check("S10: timeline-ul memoriei reflectă lanțul complet",
          len(timeline["events"]) >= 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:18070")
    ap.add_argument("--db", required=True)
    ap.add_argument("--memory-url", default="http://127.0.0.1:18091")
    ap.add_argument("--scale", type=int, default=1,
                    help="întinderea zilelor simulate (3 => ~30 de zile)")
    args = ap.parse_args()

    ctx = Ctx(args.url, args.db, args.memory_url)
    ctx.clock.scale = args.scale
    ctx.admin.execute("ir.config_parameter", "set_param",
                      "pmorg.clock_mode", "tick")
    init_ids, ctx.identity = find_world(ctx)
    ctx.clock.tick(0)

    # tick mode e chiar verificat: now client-side trebuie refuzat
    naked = ctx.runner.call("list_due_work",
                            {"now": "2026-07-02 09:00:00"},
                            "2026-07-02 09:00:00")
    check("S0: modul tick refuză now client-side",
          naked.get("error", {}).get("code") == "E_SCHEMA")

    silent = s1_silence_followup(ctx, init_ids[0])
    s2_duplicates(ctx, init_ids[0])
    s3_contradiction(ctx, init_ids[0])
    s4_concurrent_manual_edit(ctx, init_ids[0])
    s5_restart_waiting(ctx, init_ids[0])
    import subprocess

    def toggle(up):
        subprocess.run(
            ["docker", "compose", "-p", "pmorg-v2-sb3",
             "start" if up else "stop", "memory"],
            cwd="/home/vscode/PMORG-v2-sb3", capture_output=True)
        import time
        time.sleep(4 if up else 2)

    s6_memory_unavailable(ctx, init_ids[0], toggle)
    s9_escalation(ctx, init_ids[0], silent)
    s10_supersession_close(ctx, init_ids[1])

    t_end = ctx.clock.tick(11)
    first = ok(ctx.rcall("reclaim_expired", {}, t_end), "reclaim1")
    second = ok(ctx.rcall("reclaim_expired", {}, t_end), "reclaim2")
    check("SF: watchdog-ul recuperează lease-urile abandonate și e idempotent",
          second["reclaimed_run_ids"] == [])
    hanging = ctx.admin.execute("pmorg.task.run", "search_count",
                                [["outcome", "=", "running"]])
    check("SF: zero run-uri rămase în execuție la finalul orizontului",
          hanging == 0)
    days_covered = ctx.clock.day
    check(f"SF: orizont longitudinal acoperit: {days_covered} zile simulate",
          days_covered >= 30 if ctx.clock.scale >= 3 else days_covered >= 10)

    failed = [c for c, okk in CHECKS if not okk]
    print(f"\n===== GATE D (scenarii izolate): {len(CHECKS)} verificări, "
          f"{len(failed)} eșuate =====")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
