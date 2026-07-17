#!/usr/bin/env python3
"""Benchmark de extracție a grefierului (05-MEMORY-DATA §3, funcția 1).

Mesaje românești colocviale cu adevăr cunoscut → extract() real (LLM) →
scor per caz + precision/recall per kind. Rulare de CALIBRARE (fără poartă
hard încă — pragurile se fixează după prima calibrare, 05 §4).

Rulare:  PG nu e necesar.  LLM_BASE_URL/LLM_MODEL/LLM_API_KEY obligatorii.
  python3 aipm/benchmarks/extraction_bench.py
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from aipm.engine import extraction  # noqa: E402

MSG_DATE = datetime(2026, 7, 15, 10, 0)  # miercuri

INVENTORY = [
    {"code": c, "label_ro": l, "odoo_model": m, "active": True}
    for c, l, m in [
        ("PROJECT", "Proiect", "project.project"),
        ("TASK", "Task", "project.task"),
        ("PARTNER", "Partener", "res.partner"),
        ("EMPLOYEE", "Angajat", "hr.employee"),
        ("PURCHASE_ORDER", "Comandă achiziție", "purchase.order"),
        ("PRODUCT", "Produs", "product.template"),
        ("COMPANY", "Compania", "res.company"),
    ]
]

# fiecare caz: text, require=kinds obligatorii (multiset minim),
# forbid=kinds interzise, due=data așteptată (pe primul item de kind-ul dat)
CASES = [
    dict(id="E-01", text="vb cu furnizorul de lactate si iti zic pana vineri ce pret ne da",
         require=["commitment"], forbid=[], due=("commitment", "2026-07-17")),
    dict(id="E-02", text="am hotarat: mutam toate livrarile pe dimineata, incepand de luni",
         require=["decision"], forbid=[]),
    dict(id="E-03", text="la receptie am gasit doua cutii care nu apar pe factura",
         require=["observation"], forbid=["commitment", "decision"]),
    dict(id="E-04", text="cine se ocupa de comanda pentru Narcoffee saptamana asta?",
         require=["open_question"], forbid=["decision", "commitment"]),
    dict(id="E-05", text="am decis sa renuntam la meniul de vara. Eu fac maine lista noua de preturi",
         require=["decision", "commitment"], forbid=[], due=("commitment", "2026-07-16")),
    dict(id="E-06", text="ok, mersi mult!", require=[], forbid=["commitment", "decision"]),
    dict(id="E-07", text="iti promit ca rezolv pana joi factura de la decor, e la mine pe birou",
         require=["commitment"], forbid=[], due=("commitment", "2026-07-16")),
    dict(id="E-08", text="poimaine termin inventarul la bar, promit",
         require=["commitment"], forbid=[], due=("commitment", "2026-07-17")),
    dict(id="E-09", text="Mihai zicea ca poate ar rezolva el, dar nu a confirmat nimic",
         require=[], forbid=["commitment", "decision"]),
    # E-10 recalibrat: regula anunțată EXPLICIT = decision (definiția din prompt);
    # rule_candidate e rezervat tiparului implicit (E-17).
    dict(id="E-10", text="regula noua de azi: comenzile sub 100 de lei nu se mai livreaza gratuit",
         require=["decision"], forbid=["commitment"]),
    dict(id="E-11", text="n-ar trebui sa schimbam furnizorul de paine? iar au intarziat",
         require=["open_question"], forbid=["decision"]),
    dict(id="E-12", text="nu mai facem terasa luna asta, o amanam pe august — am vorbit cu Mara",
         require=["decision"], forbid=["commitment"]),
    dict(id="E-13", text="comanda PO00012 a ajuns incompleta, lipsesc 3 baxuri de apa",
         require=["observation"], forbid=[], hint=("PURCHASE_ORDER", "PO00012")),
    dict(id="E-14", text="deci am fost azi pe la depozit si e ok in mare dar frigiderul 2 face iar "
                         "zgomot si i-am zis lu Andrei ca ma ocup eu sa chem service-ul pana vineri",
         require=["commitment"], forbid=[], due=("commitment", "2026-07-17")),
    dict(id="E-15", text="platesc eu factura la curent azi si maine trimit si raportul lunar",
         require=["commitment"], forbid=["decision"]),
    dict(id="E-16", text="poate reusim candva sa refacem site-ul, ar fi frumos",
         require=[], forbid=["commitment", "decision"]),
    dict(id="E-17", text="iar am livrat gratuit o comanda de 40 de lei... de fiecare data "
                         "cand e sub 100 pierdem bani pe transport",
         require=["rule_candidate"], forbid=["decision", "commitment"]),
    dict(id="E-18", text="am decis ca de azi inchidem lunea",
         require=["decision"], forbid=["rule_candidate", "commitment"]),
]


def main():
    results = []
    tp, fp, fn = Counter(), Counter(), Counter()
    for case in CASES:
        try:
            items = extraction.extract(case["text"], "Autor Test", 201,
                                       MSG_DATE, INVENTORY)
        except Exception as exc:
            results.append((case["id"], False, f"EXCEPȚIE: {exc}"))
            for k in case["require"]:
                fn[k] += 1
            continue
        got = Counter(i.kind for i in items)
        need = Counter(case["require"])
        problems = []
        for kind, cnt in need.items():
            have = min(got.get(kind, 0), cnt)
            tp[kind] += have
            if got.get(kind, 0) < cnt:
                fn[kind] += cnt - got.get(kind, 0)
                problems.append(f"lipsă {kind}")
        for kind in case["forbid"]:
            if got.get(kind, 0):
                fp[kind] += got[kind]
                problems.append(f"inventat {kind}")
        for kind, cnt in got.items():
            extra = cnt - need.get(kind, 0)
            if extra > 0 and kind not in case["forbid"]:
                fp[kind] += 0  # kind tolerat (ex. observation în plus) — nu penalizăm
        if "due" in case:
            dkind, ddate = case["due"]
            dues = [str(i.due_at) for i in items if i.kind == dkind and i.due_at]
            if ddate not in dues:
                problems.append(f"termen greșit: {dues or 'lipsă'} ≠ {ddate}")
        if "hint" in case:
            hcode, htext = case["hint"]
            hits = [e for i in items for e in i.entities
                    if e.anchor_code_hint == hcode and htext.lower() in e.normalized_text.lower()]
            if not hits:
                problems.append(f"entitate {hcode}:{htext} nerecunoscută")
        results.append((case["id"], not problems, "; ".join(problems) or "ok"))

    print(f"\n=== Extracție — model: {os.environ.get('LLM_MODEL')} ===")
    passed = 0
    for cid, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {detail}")
        passed += ok
    print(f"\nCazuri: {passed}/{len(CASES)}")
    for kind in ("commitment", "decision", "observation", "open_question", "rule_candidate"):
        p = tp[kind] / (tp[kind] + fp[kind]) if (tp[kind] + fp[kind]) else None
        r = tp[kind] / (tp[kind] + fn[kind]) if (tp[kind] + fn[kind]) else None
        fmt = lambda v: f"{v:.2f}" if v is not None else "—"
        print(f"  {kind:15s} precision={fmt(p)} recall={fmt(r)}")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
