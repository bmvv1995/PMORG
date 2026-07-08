# pm-org — repo-ul de unificare al produsului „PM organizațional"

> Nume de lucru. Creat 2026-07-08, când cele două linii ale proiectului au
> fost declarate compatibile și s-a decis unificarea. Acesta e **casa
> produsului** și repo-ul pe care se dezvoltă planul de integrare —
> auto-suficient: tot ce e nevoie pentru planificare e aici, nu în memoria
> vreunei sesiuni.

Documentul-lege: [`docs/INTENT-UNIFICARE.md`](docs/INTENT-UNIFICARE.md) —
componentele, principiile P1–P6, joncțiunea unică, fluxurile de integrat,
amendamentele la moștenire, necunoscutele deschise.

## Structura repo-ului

```
docs/
  INTENT-UNIFICARE.md            legea unificării (2026-07-08)
  aipm/                          documentele componentei de memorie:
                                 INTENT_AIPM, SPEC_AIPM (§0–§1 închise),
                                 PLAN_AIPM_V1, FLUX_ACTUAL (harta nous), INTENT (nous)
  mostenire-pm-organizational/   linia de definiție 2026-07-06: definiția
                                 funcțională, spec v0.3, două analize externe,
                                 analiza de gap, puncte de clarificare
aipm/                            CODUL memoriei ancorate (Fazele 0+1 implementate):
                                 adaptor Odoo (conectorii: contract + XML-RPC + fake
                                 cu fixtures), motor (extracție/rezoluție/recall/
                                 chitanțe), migrări PG, ingest, rapoarte, UI, teste
components/                      instantanee ale codului viu de pe server
                                 (doar fișiere urmărite de git, fără secrete):
  hermes-ops-mcp/                serverul MCP cu uneltele îngrădite ale PM-ului (@257f428)
  cc-bridge/                     puntea Hermes↔Claude Code: shim + unitate systemd (@9a1ab0e)
  pm-organizational/             installer-ul + template-urile produsului (@065e36e)
```

**Sursa vie vs instantaneu:** `aipm/` de aici provine din
https://github.com/bmvv1995/aipm (@7156087) și devine sursa de dezvoltare;
`components/` sunt instantanee datate — sursa vie rămâne pe server
(204.168.208.233: `~/.hermes`, `~/cc-bridge`, `~/hermes-ops-mcp`,
`~/pm-organizational`, servicii systemd). La modificări pe server,
instantaneele se reîmprospătează cu `git archive`.

## Componentele produsului (rolurile, pe scurt)

| Componentă | Rol unic |
|---|---|
| **PM pe Claude Code** (creierul) | orchestrator cu unelte îngrădite fizic; consumator read-only de memorie |
| **Hermes + puntea** (corpul de proces) | kanban cu gări, gateway Telegram, ceas, ritual de aprobare — aparatul circulator |
| **aipm** (memoria) | sedimentarea: fapte ancorate în Odoo, chitanță în chatter, claims validate mecanic |
| **Odoo** (sursa formală) | scheletul lumii — instanța horeca, populată cu date reale |

## Mediul de integrare și test

- Server 204.168.208.233: stack-ul de proces viu (board, gateway pm, cron, punte).
- Odoo populat (instanța horeca, per `docs/aipm/SPEC_AIPM.md` §0):
  integrarea se testează pe date adevărate; `ODOO_ADAPTER=fake` pentru
  testele deterministe locale.

## Ce urmează aici

1. [`docs/PLAN-INTEGRARE.md`](docs/PLAN-INTEGRARE.md) — ordinea etapelor cu
   criterii de ieșire verificabile și deciziile consemnate (2026-07-08).
2. Compoziția: instalarea componentelor împreună, moștenind installer-ul.
