#!/usr/bin/env python3
"""Smoke scenario PMORG (02-MVP §8) — runner determinist, fără LLM.

Pașii care cer memoria reală prin MCP (Gate B) sunt marcați STUB și
consemnați ca referințe de dovadă la nivel de contract. Scenariul devine
complet abia după integrarea memoriei; acest script validează bucla
Odoo ↔ runner ↔ canal simulat.
"""

import argparse
import sys

from pmorg_runner.channel import SimulatedChannel
from pmorg_runner.client import OdooApiClient
from pmorg_runner.clock import VirtualClock

CHECKS = []


def check(name, condition, detail=""):
    CHECKS.append((name, bool(condition), detail))
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail and not condition else ""))
    return bool(condition)


def get_result(resp, context):
    if resp.get("status") not in ("ok", "replay"):
        raise RuntimeError(f"{context}: {resp.get('error')}")
    return resp["result"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18070")
    parser.add_argument("--db", default="pmorg_smoke")
    parser.add_argument("--login", default="admin")
    parser.add_argument("--password", default="admin")
    args = parser.parse_args()

    clock = VirtualClock("2026-07-16 08:00:00")
    api = OdooApiClient(args.url, args.db, args.login, args.password)
    channel = SimulatedChannel(
        {
            "victor.neagu": [
                "Criteriul de acceptare e livrarea validată de Paul, "
                "până vineri. Nu l-am trecut nicăieri în scris."
            ]
        }
    )

    # -- 1–2. Mara creează inițiativa, obiectivul și criteriul (rol uman) ----
    company = api.execute(
        "res.company", "search", [["name", "=", "Atelier Minimal Test SRL"]]
    )
    check("Compania sintetică există (demo încărcat)", company)
    # Fixture: operatorul uman primește acces la compania sintetică
    # (record rules multi-company ascund altfel lumea Delta).
    api.execute("res.users", "write", [api.uid], {"company_ids": [(4, company[0])]})
    project = api.execute(
        "project.project", "search",
        [["name", "=", "Coordonare internă — TEST"]],
    )
    victor = api.execute(
        "pmorg.identity", "search", [["name", "=", "Victor Neagu"]], limit=1
    )
    owner = api.execute(
        "pmorg.identity", "search", [["name", "=", "Ana Dobre"]], limit=1
    )
    initiative_id = api.execute(
        "pmorg.initiative", "create",
        {
            "name": "MIN-001 — smoke run",
            "objective": "Stabilirea criteriului de acceptare și finalizarea livrabilului",
            "project_id": project[0],
            "company_id": company[0],
            "owner_identity_id": owner[0],
        },
    )
    criterion_id = api.execute(
        "pmorg.success.criterion", "create",
        {
            "name": "Criteriu confirmat și livrabil finalizat cu dovadă",
            "initiative_id": initiative_id,
        },
    )
    check("Pas 1–2: inițiativă + obiectiv + criteriu create", initiative_id)

    # -- 3. PMORG creează taskul agentic de clarificare ----------------------
    resp = api.call(
        "propose_task",
        {
            "initiative_id": initiative_id,
            "name": "Obține criteriul de acceptare lipsă (smoke)",
            "pmorg_task_type": "clarification",
            "execution_mode": "agent",
            "expected_outcome": "Criteriu de acceptare explicit, confirmat",
            "participant_ids": victor,
        },
        clock.now,
    )
    task_id = get_result(resp, "propose_task")["task_id"]
    check("Pas 3: task agentic creat prin contract, stare ready", task_id)

    # -- 4. Claim atomic + claim concurent refuzat + replay ------------------
    claim_key = api.next_key("claim")
    claim = get_result(
        api.call("claim_task", {"task_id": task_id, "now": clock.now},
                 clock.now, key=claim_key),
        "claim_task",
    )
    run_ref = {
        "task_id": task_id,
        "run_id": claim["run_id"],
        "lease_token": claim["lease_token"],
    }
    rival = OdooApiClient(args.url, args.db, args.login, args.password,
                          actor_id="runner-rival")
    rival_resp = rival.call("claim_task", {"task_id": task_id, "now": clock.now},
                            clock.now)
    check(
        "Pas 4a: claim concurent refuzat (E_LEASE_HELD)",
        rival_resp.get("error", {}).get("code") == "E_LEASE_HELD",
        str(rival_resp.get("error")),
    )
    replay = api.call("claim_task", {"task_id": task_id, "now": clock.now},
                      clock.now, key=claim_key)
    check(
        "Pas 4b: retry-ul aceluiași claim întoarce replay, același run",
        replay.get("status") == "replay"
        and replay["result"]["run_id"] == claim["run_id"],
        str(replay),
    )

    # -- 5. Canalul simulat: întrebare + așteptare + răspuns scriptat --------
    get_result(api.call("record_progress", dict(run_ref, note="contact inițial"),
                        clock.now), "record_progress")
    channel.send_message("victor.neagu",
                         "Bună, care e criteriul de acceptare pentru MIN-001?",
                         "smoke-XNX-001", clock.now)
    get_result(
        api.call(
            "record_waiting_response",
            dict(run_ref, awaiting_identity_id=victor[0]),
            clock.now,
        ),
        "record_waiting_response",
    )

    # -- SIMULARE RESTART: client nou, starea vine din Odoo ------------------
    api2 = OdooApiClient(args.url, args.db, args.login, args.password)
    state = get_result(
        api2.call("get_task_state", {"task_id": task_id}, clock.now),
        "get_task_state",
    )
    check(
        "Restart: starea supraviețuiește (waiting_response, run activ)",
        state["orchestration_state"] == "waiting_response"
        and bool(state["active_run"]),
        str(state),
    )
    api = api2  # continuăm cu procesul „repornit”

    # Așteptare lungă = protocol episodic: eliberăm lease-ul și programăm
    # revenirea (ADR-007). Nu ținem lease-uri peste ore de tăcere.
    next_check = "2026-07-16 10:00:00"
    get_result(
        api.call(
            "schedule_next_check",
            dict(run_ref, next_check_at=next_check, reason="aștept răspuns"),
            clock.now,
        ),
        "schedule_next_check",
    )
    clock.advance(hours=2)
    reply = channel.receive_reply("victor.neagu", "smoke-XNX-001", clock.now)
    check("Pas 5: răspuns scriptat primit, identitate structurală",
          reply and reply["verified_sender_identity"] == "victor.neagu")

    # Revendicare nouă la scadență (run #2 pe același task — 01-ARCH §4.2).
    claim2 = get_result(
        api.call("claim_task", {"task_id": task_id, "now": clock.now}, clock.now),
        "claim #2",
    )
    run_ref = {
        "task_id": task_id,
        "run_id": claim2["run_id"],
        "lease_token": claim2["lease_token"],
    }

    # -- 6–7. Evidența răspunsului (STUB memorie — Gate B) -------------------
    evidence_ref = f"mem://evidence/{reply['content_hash'][:16]}"
    get_result(
        api.call(
            "record_evidence_reference",
            {
                "task_id": task_id,
                "memory_ref": evidence_ref,
                "kind": "conversation_reply",
                "note": "STUB Gate B: va deveni memory_capture_evidence prin MCP",
            },
            clock.now,
        ),
        "record_evidence_reference",
    )
    check("Pas 6–7 (STUB): evidența referențiată la nivel de contract", True)

    # -- Reluare + finalizare run clarificare --------------------------------
    get_result(api.call("record_progress",
                        dict(run_ref, note="răspuns corelat, concluzie extrasă"),
                        clock.now), "record_progress")
    done = api.call(
        "complete_run",
        dict(run_ref, outcome="done",
             summary="Criteriul: livrare validată de Paul până vineri",
             evidence_refs=[evidence_ref]),
        clock.now,
    )
    check("Run clarificare finalizat, orchestrare=completed",
          get_result(done, "complete_run")["orchestration_state"] == "completed")
    runs = api.execute("pmorg.task.run", "search_count",
                       [["task_id", "=", task_id]])
    check("Task clarificare are 2 run-uri distincte (episodic)", runs == 2,
          f"runs={runs}")

    # -- 9. Taskul operațional rezultat --------------------------------------
    op = get_result(
        api.call(
            "propose_task",
            {
                "initiative_id": initiative_id,
                "name": "Finalizează livrabilul conform criteriului confirmat (smoke)",
                "pmorg_task_type": "execution",
                "execution_mode": "human",
            },
            clock.now,
        ),
        "propose_task",
    )
    clock.advance(days=1)
    op_ref_claim = get_result(
        api.call("claim_task", {"task_id": op["task_id"], "now": clock.now},
                 clock.now),
        "claim op",
    )
    op_ref = {
        "task_id": op["task_id"],
        "run_id": op_ref_claim["run_id"],
        "lease_token": op_ref_claim["lease_token"],
    }
    get_result(api.call("record_progress", dict(op_ref, note="acțiune aplicată"),
                        clock.now), "progress op")
    # -- 10. Finalizare cu dovadă distinctă ----------------------------------
    get_result(
        api.call(
            "complete_run",
            dict(op_ref, outcome="done", summary="Livrabil finalizat conform criteriului",
                 evidence_refs=["mem://evidence/TEST-EVID-XNX-001"]),
            clock.now,
        ),
        "complete op",
    )
    check("Pas 9–10: task operațional creat, executat, dovadă distinctă", True)

    # -- 11. Închiderea refuzată fără criteriu verificat, apoi închisă -------
    api.execute("pmorg.initiative", "write", [initiative_id],
                {"state": "verifying"})
    refused = False
    try:
        api.execute("pmorg.initiative", "action_close", [initiative_id])
    except Exception:
        refused = True
    check("Pas 11a: închidere refuzată cu criteriu neverificat", refused)
    api.execute("pmorg.success.criterion", "action_mark_verified", [criterion_id])
    api.execute("pmorg.initiative", "action_close", [initiative_id])
    state = api.execute("pmorg.initiative", "read", [initiative_id],
                        ["state", "close_date"])[0]
    check("Pas 11b: inițiativa închisă după verificarea criteriului",
          state["state"] == "closed" and state["close_date"])

    # -- 12. Timeline-ul reconstruiește lanțul -------------------------------
    events = api.execute(
        "pmorg.task.event", "search_read",
        [["task_id", "in", [task_id, op["task_id"]]]],
        ["event_type", "task_id", "run_id"],
    )
    types = [e["event_type"] for e in events]
    expected_chain = ["task.ready", "task.claimed", "task.progress",
                      "task.waiting_response", "task.evidence_reference",
                      "task.run_completed"]
    check(
        "Pas 12: timeline complet (ready→claimed→progress→waiting→evidence→completed)",
        all(t in types for t in expected_chain),
        f"lipsesc: {[t for t in expected_chain if t not in types]}",
    )

    # -- Raport ---------------------------------------------------------------
    failed = [c for c in CHECKS if not c[1]]
    print("\n===== RAPORT SMOKE =====")
    print(f"{len(CHECKS)} verificări, {len(failed)} eșuate")
    print("Limitare asumată: pașii de memorie (6–8) sunt STUB până la Gate B.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
