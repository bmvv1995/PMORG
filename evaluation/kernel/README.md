# Kernelul de evaluare — v0 (Gate A minim)

Rulare: `python3 evaluation/kernel/run_bundle.py --run-id <id>` — o comandă:
provisionare proiect compose izolat (volume proprii) → instalare 3 profiluri
→ scenariul smoke ×3 → probe → verdict sigilat → distrugerea volumelor.

## Implementat (v0) vs proiectat (DoD 06-EVALUATION-SANDBOX §13)

| Cerință | Stare |
|---|---|
| 1 o comandă provision→run→report→destroy | ✅ |
| 2–3 zero producție, fail-closed la config | ✅ (moștenit din memorie/compose) |
| 4 doar loopback publicat | ✅ |
| 6 oracle inaccesibil SUT + probă negativă | ✅ v0: oracle doar pe mașina evaluatorului; probă mount + canary scan pe loguri |
| 8 bundle fixează commit/imagini/contracte/profile | ✅ manifest public cu hash |
| 11 trasă append-only hash-chained | ✅ journal.jsonl |
| 15 run întrerupt ⇒ INVALID, nu PASS | ✅ |
| 16 reset `down -v` | ✅ (credențiale noi per run: proiectat) |
| 5 hardening containere (cap_drop, no-new-priv) | 🔶 proiectat — preluare din șablonul sb2 |
| 7 oracle DB separat cu rol propriu | 🔶 v0: oracle = fișiere locale evaluator, nu DB |
| 9 worldgen determinist cu world.lock | 🔶 proiectat (lumile sunt demo packs) |
| 10 tick_id neforjabil server-side | 🔶 proiectat — contract 2.0 (nota din 07-CONTRACTS §9) |
| 12 checkpointuri sigilate per tick, as_of_event_seq | 🔶 proiectat |
| 13 scorer cu citare de dovezi per metrică | 🔶 v0: scor agregat pe unități așteptate |
| 14 splituri corpus + hidden labels | 🔶 proiectat (intră cu corpusul, 05-MEMORY-DATA) |
| 17 reproducerea unui run eșuat din bundle | 🔶 parțial: comanda de repro în verdict |
| semnătura verdictului | 🔶 hash (semnătura criptografică: întrebare deschisă §16.8) |

Primul run: `runs/mvp001/` — verdict VALID/PASS, 25/25 × 3 profiluri.
