# Raport Gate D — calificarea longitudinală (S6)

| Câmp | Valoare |
|---|---|
| Data | 2026-07-18 |
| Mediu | sb3, lumi worldgen (seed 42), memorie aipm-sub-contract, ceas trusted |
| Verdict propus | **verde** — verdictul formal aparține ownerului |

## Rezultate

**Scenariile izolate + orizontul de 33 de zile simulate** (`run_longitudinal.py --scale 3`,
mod `pmorg.clock_mode=tick` — now client-side refuzat, verificat ca S0):
**26/26 verificări.** S1 tăcere + exact un follow-up; S2 duplicate (comandă
replay + evidență dedup); S3 contradicție vizibilă → supersession fără
ștergere; S4 editare manuală concurentă (lease intact, conflict optimist
refuzat explicit, schimbarea vizibilă pentru reconciliere prin tracking);
S5 restart în `waiting_response` (stare 100% din Odoo, firul continuă);
S6 memorie indisponibilă (eroare explicită, orchestrarea deterministă
continuă, retry sigur după revenire); S9 escaladare conform politicii
(eveniment append-only); S10 supersession + închidere refuzată fără criteriu
verificat; SF watchdog idempotent, zero run-uri suspendate la orizont.

**S7 Inventory (profil distribuție): 5/5** — transfer sintetic real
(`stock.picking` + `stock.move` confirmate), claim ancorat
INVENTORY_TRANSFER/INVENTORY_MOVE, recall funcțional, profilul minimal
refuză ancora fail-closed.

**S8 Time Off (profil servicii): 6/6** — pack nou `pmorg_anchor_time_off`
(schema-check la instalare), absență `hr.leave` reală, suprapunere
termen-absență detectată determinist, replanificare peste fereastra
absenței, claim ancorat LEAVE_REQUEST, profilul minimal refuză fail-closed.

**Regresie:** suita `pmorg_core` 49/49; comenzile noi (contract 1.1 aditiv):
`record_followup`, `record_escalation`.

## Limitări consemnate

1. S8 a rulat în modul `client` al ceasului (datele absenței sunt explicite);
   S1–S10 restul pe tick.
2. Detectorul D1 rămâne cu granularitate per-înregistrare
   (benchmark S5: precision 1.00 / recall 0.50) — calibrare F3.
3. Rulările folosesc kernelul v0 (matricea implementat-vs-proiectat din
   `evaluation/kernel/README.md`); run bundle sigilat pentru Gate D — pasul
   următor de integrare.

Conform 02-MVP: cu Gate D verde, afirmația permisă devine „arhitectura e
calificată longitudinal"; „operator persistent validat" complet cere și
Gate E (operatorul AI) + F2 (Hermes).
