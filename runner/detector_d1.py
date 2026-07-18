#!/usr/bin/env python3
"""Controllerul D1 — efect fără cauză (08-MEMORY-CHANNELS, L1/F1).

Determinist, episodic: citește schimbările materiale din Odoo (tracking),
verifică în memoria reală dacă vreo amintire ancorată le explică, consemnează
golurile și raportează rata de acoperire. Nu decide nimic — întreabă.
"""

import argparse
import sys

from pmorg_runner.client import OdooApiClient
from pmorg_runner.memory_client import MemoryClient

ANCHOR_FOR_MODEL = {
    "pmorg.initiative": "INITIATIVE",
    "project.task": "TASK",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:18070")
    ap.add_argument("--db", required=True)
    ap.add_argument("--login", default="admin")
    ap.add_argument("--password", default="admin")
    ap.add_argument("--memory-url", required=True)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD HH:MM:SS")
    ap.add_argument("--now", required=True)
    args = ap.parse_args()

    api = OdooApiClient(args.url, args.db, args.login, args.password,
                        actor_id="detector-d1")
    mem = MemoryClient(args.memory_url)

    resp = api.call("list_material_changes", {"since": args.since}, args.now)
    changes = resp["result"]["changes"]
    covered, gaps = 0, []
    for change in changes:
        anchor_type = ANCHOR_FOR_MODEL.get(change["model_name"])
        if not anchor_type:
            continue
        recall = mem.ok("memory_recall", anchor={
            "anchor_type": anchor_type,
            "model": change["model_name"],
            "res_id": change["res_id"],
        })
        if recall["claims"]:
            covered += 1
            continue
        gap = api.call("record_provenance_gap", dict(
            change,
            summary=(f"{change['model_name']}#{change['res_id']}."
                     f"{change['field_name']} schimbat la "
                     f"{change['changed_at']} — nicio decizie consemnată. "
                     f"Cine și unde a decis?"),
        ), args.now)
        gaps.append((gap["result"]["gap_id"], gap["result"]["replayed"],
                     change))

    total = covered + len(gaps)
    rate = (covered / total * 100) if total else 100.0
    print(f"D1: {len(changes)} schimbări materiale, {covered} cu proveniență, "
          f"{len(gaps)} goluri")
    print(f"Rata de acoperire: {rate:.0f}%")
    for gap_id, replayed, change in gaps:
        mark = "=" if replayed else "+"
        print(f" [{mark}] gap#{gap_id}: {change['model_name']}"
              f"#{change['res_id']}.{change['field_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
