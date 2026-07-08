#!/usr/bin/env python3
"""Audit determinist al board-ului (forclarify #4). Fără LLM: doar SQL.

Rulează ca cron --no-agent: stdout gol = tăcere; stdout nevid = livrat
ownerului. Detectează încălcări MĂSURABILE ale convențiilor de board:
  - task închis fără ARTEFACT (nici comment cu ARTEFACT:, nici result substanțial)
  - task running fără niciun comment de >3 zile (stagnare tăcută)
  - task blocked de >3 zile (om care nu răspunde / nud lipsă)
Nu măsoară calitatea conținutului — doar prezența și vârsta. Restul e al omului.
"""
import sqlite3
import time

DB = "/home/vscode/.hermes/kanban.db"
ZI = 86400
MIN_RESULT = 40  # caractere; sub asta result-ul e considerat de mântuială

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
acum = time.time()
probleme = []


def ts(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


for r in db.execute("""
    SELECT t.id, t.title, t.status, t.result,
           COALESCE(t.started_at, t.created_at) AS activ_de,
           (SELECT COUNT(*) FROM task_comments c WHERE c.task_id=t.id
              AND c.body LIKE '%ARTEFACT:%') AS n_artefacte,
           (SELECT MAX(c.created_at) FROM task_comments c WHERE c.task_id=t.id)
              AS ultim_comment
    FROM tasks t WHERE t.status NOT IN ('archived')"""):
    titlu = (r["title"] or "")[:50]
    if r["status"] == "done":
        result_ok = r["result"] and len(r["result"].strip()) >= MIN_RESULT
        if not r["n_artefacte"] and not result_ok:
            n = len((r["result"] or "").strip())
            probleme.append(f"• {r['id']} «{titlu}»: ÎNCHIS FĂRĂ ARTEFACT "
                            f"(result: {n} caractere)")
    elif r["status"] == "running":
        ultim = ts(r["ultim_comment"]) or ts(r["activ_de"]) or acum
        zile = (acum - ultim) / ZI
        if zile > 3:
            probleme.append(f"• {r['id']} «{titlu}»: RUNNING, tăcere de {zile:.0f} zile")
    elif r["status"] == "blocked":
        vechime = (acum - (ts(r["ultim_comment"]) or ts(r["activ_de"]) or acum)) / ZI
        if vechime > 3:
            probleme.append(f"• {r['id']} «{titlu}»: BLOCKED de {vechime:.0f} zile")

if probleme:
    print("🔎 Audit board — abateri de la convenții:")
    print("\n".join(probleme))
