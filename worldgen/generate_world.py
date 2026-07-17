#!/usr/bin/env python3
"""Worldgen v1 (ADR-016, S5): lume sintetică deterministă din seed.

Nucleul cunoaște doar: identități, structură, proiect, inițiative, taskuri,
calendar de evenimente și materializare. Incidentele au adevăr cunoscut —
`covered` (decizie consemnată: evidență+claim în memorie ÎNAINTE de efect) și
`dark` (efect fără consemnare) — deci detectorul D1 devine măsurabil P/R.

Determinism: același (profil, seed, days, versiune) ⇒ același plan canonic ⇒
același world.lock. Fără ceas de perete în plan: datele sim derivă din epocă.

  generate  --profile org-min --seed 42 --days 10 --out <dir>
  materialize --plan <dir>/plan.json --db <db> [--url/--memory-url]
"""

import argparse
import hashlib
import json
import pathlib
import random
import sys

GENERATOR_VERSION = "1.0"
EPOCH = "2026-07-01"

FIRST = ["Ana", "Paul", "Victor", "Elena", "Dan", "Ioana", "Mara", "Andrei",
         "Mihai", "Radu", "Sorina", "Vlad"]
LAST = ["Dobre", "Rusu", "Neagu", "Marin", "Petre", "Sava", "Ionescu", "Pop",
        "Stan", "Toma", "Enache", "Georgescu"]
COMPANY_FOR = {
    "org-min": "Atelier WG Test SRL",
    "org-services": "Birou WG Test SRL",
    "org-distribution": "Delta WG Test SRL",
}
MATERIAL_TASK_FIELDS = ["pmorg_task_type", "date_deadline"]
TASK_TYPES = ["execution", "clarification", "followup", "monitoring"]


def sim_date(day, hour=9):
    from datetime import datetime, timedelta
    base = datetime.fromisoformat(EPOCH)
    return (base + timedelta(days=day, hours=hour)).strftime(
        "%Y-%m-%d %H:%M:%S")


def generate(profile, seed, days):
    rng = random.Random(f"{profile}:{seed}:{GENERATOR_VERSION}")
    people = rng.sample([f"{f} {l}" for f in FIRST for l in LAST], 4)
    initiatives = []
    for idx in range(2):
        code = f"WG{seed}-{idx + 1:03d}"
        initiatives.append({
            "code": code,
            "name": f"{code} — inițiativă generată",
            "objective": f"Obiectiv sintetic {code}",
            "tasks": [
                {"key": f"{code}-T{t + 1}",
                 "name": f"Task {t + 1} pentru {code}",
                 "task_type": rng.choice(TASK_TYPES)}
                for t in range(2)
            ],
        })
    incidents = []
    all_tasks = [(i["code"], t["key"]) for i in initiatives for t in i["tasks"]]
    current = {t["key"]: dict(pmorg_task_type=t["task_type"], date_deadline=None)
               for i in initiatives for t in i["tasks"]}
    for day in range(1, days + 1):
        if rng.random() < 0.6:
            code, task_key = rng.choice(all_tasks)
            field = rng.choice(MATERIAL_TASK_FIELDS)
            if field == "pmorg_task_type":
                new_value = rng.choice(
                    [t for t in TASK_TYPES
                     if t != current[task_key]["pmorg_task_type"]])
            else:
                new_value = sim_date(day + rng.randint(3, 10))[:10]
                if new_value == current[task_key]["date_deadline"]:
                    new_value = sim_date(day + 15)[:10]
            current[task_key][field] = new_value
            incidents.append({
                "id": f"INC-{seed}-{day:02d}",
                "day": day,
                "target": {"kind": "task", "key": task_key},
                "field": field,
                "new_value": new_value,
                "covered": rng.random() < 0.5,
                "author": rng.choice(people),
            })
    plan = {
        "generator_version": GENERATOR_VERSION,
        "profile": profile,
        "seed": seed,
        "days": days,
        "epoch": EPOCH,
        "company": COMPANY_FOR[profile],
        "people": [
            {"name": people[0], "role": "owner", "has_user": True},
            {"name": people[1], "role": "validator", "has_user": False},
            {"name": people[2], "role": "participant", "has_user": False},
            {"name": people[3], "role": "participant", "has_user": False},
        ],
        "project": f"Proiect generat — {profile} #{seed}",
        "initiatives": initiatives,
        "incidents": incidents,
    }
    canonical = json.dumps(plan, sort_keys=True, ensure_ascii=False)
    lock = hashlib.sha256(canonical.encode()).hexdigest()
    oracle = {
        "world_lock": lock,
        "expected_gaps": [i["id"] for i in incidents if not i["covered"]],
        "expected_covered": [i["id"] for i in incidents if i["covered"]],
    }
    return plan, lock, oracle


def materialize(plan, url, db, login, password, memory_url):
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "runner"))
    from pmorg_runner.client import OdooApiClient
    from pmorg_runner.memory_client import MemoryClient

    api = OdooApiClient(url, db, login, password, actor_id="worldgen")
    mem = MemoryClient(memory_url)

    def ex(model, method, *args, **kw):
        return api.execute(model, method, *args, **kw)

    company = ex("res.company", "create", {"name": plan["company"]})
    ex("res.users", "write", [api.uid], {"company_ids": [(4, company)]})
    slug = plan["company"].lower().replace(" ", ".")
    identities = {}
    for person in plan["people"]:
        partner = ex("res.partner", "create", {
            "name": person["name"], "company_id": company,
            "email": f"{person['name'].lower().replace(' ', '.')}@{slug}.example",
        })
        identities[person["name"]] = ex("pmorg.identity", "create", {
            "partner_id": partner, "company_id": company})
    project = ex("project.project", "create",
                 {"name": plan["project"], "company_id": company})
    records = {}
    owner_name = plan["people"][0]["name"]
    for init in plan["initiatives"]:
        init_id = ex("pmorg.initiative", "create", {
            "name": init["name"], "objective": init["objective"],
            "project_id": project, "company_id": company,
            "owner_identity_id": identities[owner_name],
        })
        records[init["code"]] = ("pmorg.initiative", init_id)
        for task in init["tasks"]:
            task_id = ex("project.task", "create", {
                "name": task["name"], "project_id": project,
                "company_id": company, "pmorg_initiative_id": init_id,
                "pmorg_task_type": task["task_type"],
            })
            records[task["key"]] = ("project.task", task_id)

    applied = []
    for inc in plan["incidents"]:
        model, res_id = records[inc["target"]["key"]]
        if inc["covered"]:
            ev = mem.ok("memory_capture_evidence",
                        external_id=f"wg-{inc['id']}",
                        source="worldgen:conversation",
                        author_ref=f"wg:{inc['author']}",
                        content=(f"Am decis: {inc['field']} devine "
                                 f"{inc['new_value']} ({inc['id']})."))
            mem.ok("memory_propose_claim",
                   statement=f"Decizie {inc['id']}: {inc['field']} -> "
                             f"{inc['new_value']}",
                   author_ref=f"wg:{inc['author']}",
                   evidence_ids=[ev["evidence_id"]],
                   anchors=[{"anchor_type": "TASK", "model": model,
                             "res_id": res_id, "role": "subject"}])
        ex(model, "write", [res_id], {inc["field"]: inc["new_value"]})
        applied.append({"id": inc["id"], "model": model, "res_id": res_id,
                        "field": inc["field"], "covered": inc["covered"]})
    return {"company_id": company, "applied": applied}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--profile", required=True, choices=sorted(COMPANY_FOR))
    g.add_argument("--seed", type=int, required=True)
    g.add_argument("--days", type=int, default=10)
    g.add_argument("--out", required=True)
    m = sub.add_parser("materialize")
    m.add_argument("--plan", required=True)
    m.add_argument("--db", required=True)
    m.add_argument("--url", default="http://127.0.0.1:18070")
    m.add_argument("--login", default="admin")
    m.add_argument("--password", default="admin")
    m.add_argument("--memory-url", default="http://127.0.0.1:18091")
    args = ap.parse_args()

    if args.cmd == "generate":
        plan, lock, oracle = generate(args.profile, args.seed, args.days)
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "plan.json").write_text(
            json.dumps(plan, indent=1, ensure_ascii=False, sort_keys=True))
        (out / "world.lock").write_text(lock)
        (out / "oracle.json").write_text(json.dumps(oracle, indent=1))
        print(f"world.lock: {lock}")
        print(f"incidente: {len(plan['incidents'])} "
              f"(dark: {len(oracle['expected_gaps'])})")
    else:
        plan = json.loads(pathlib.Path(args.plan).read_text())
        result = materialize(plan, args.url, args.db, args.login,
                             args.password, args.memory_url)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
