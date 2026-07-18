# HANDOFF — preluarea sesiunii de orchestrare PMORG

| | |
|---|---|
| Data | 2026-07-18 |
| Autor | Claude (sesiunea de orchestrare, laptop owner) |
| Scop | orice sesiune nouă (alt context, alt host, VPS) să poată prelua rolul integral, doar din GitHub |
| Anexa privată | issue „HANDOFF — anexa de infrastructură" în `bmvv1995/PMORG-Platform` (repo privat; acolo stau detaliile de acces care nu au ce căuta într-un repo public) |

## 0. Bootstrap (ordinea exactă)

1. `git clone https://github.com/bmvv1995/PMORG && cd PMORG` (sau `git pull` dacă există deja).
2. `gh auth status` — contul trebuie să vadă și repo-ul privat `bmvv1995/PMORG-Platform`.
3. Citește, în ordine: acest fișier → `docs/correspondence/` (toate, numerotate) → PR-urile deschise (`gh pr list`) → ultimele comentarii pe [Issue #16 din PMORG-Platform](https://github.com/bmvv1995/PMORG-Platform/issues/16).
4. Repornește veghea (§5) — ea NU supraviețuiește sesiunii care a creat-o.
5. Abia apoi lucrează.

## 1. Ce este proiectul, într-un paragraf

PMORG = operator organizațional persistent ancorat în Odoo, cu **memoria guvernată** ca diferențiator: evidență → claims ancorate → chitanțe, nimic normativ fără înregistrare. v2 (`docs/pmorg-v2/`, `odoo_addons/pmorg_core`, `aipm/`, `worldgen/`, `runner/`, `evaluation/`) e construit și verde până la Gate D (calificare longitudinală, raport `docs/pmorg-v2/09-GATE-D-REPORT.md`). v3 (`docs/pmorg-v3/`, suita lui Sol) e baseline-ul canonic de cerințe pentru CPMORG — nucleul PMORG integrat în Onyx, cu ancorarea Odoo păstrată.

## 2. Actorii și protocolul de colaborare

- **Ownerul (Bogdan)**: singura autoritate pe merge în master pentru canon și pe deciziile de principiu. Lucrează prin mandate delegate; nu-l notifica informativ, escaladează doar decizii.
- **Sol (GPT-5.6, sesiune Codex)**: deep-context, temele de integrare CPMORG/Onyx; lucrează pe `sol/*`, are repo-ul privat `PMORG-Platform` (fork Onyx guvernat; directorul `ee/` NU se atinge — licență enterprise).
- **Claude (rolul pe care îl preiei)**: orchestrare, sedimentare, review încrucișat; branch-uri `claude/*`.
- **Protocolul complet**: `docs/correspondence/000-claude-catre-sol.md` (fondator) + amendamentul din `001` (§final): **fiecare sesiune începe cu `git pull` + citirea corespondenței noi și a PR-urilor**. Repo-ul e singurul canal; Issue #16 din PMORG-Platform e inbox-ul lui Sol; afirmațiile se ancorează (commit, `fișier:linie`, output de suită), altfel se etichetează `[speculație]`; dezacordurile se tranșează cu starea, iar dacă nu se poate — se urcă la owner cu ambele poziții scrise.

## 3. Legile care nu se negociază (decizii de owner, nu de agenți)

Din `docs/pmorg-v2/08-MEMORY-CHANNELS.md` §2.7–2.8:

1. **HIL = exclusiv vocabular** (entități recurente noi, tipuri noi de ancoră, matching ambiguu de ancoră cu consecință). Interpretarea NU ajunge niciodată la om; `needs_review` nu e coadă umană.
2. **Poarta înaintea conductei**: identitate structurală (autor nemapat ⇒ carantină), denylist de intimitate ÎNAINTE de stocare (refuz consemnat FĂRĂ conținut).
3. **Detectorul golului** = mecanismul de autocalibrare a vocabularului (nu coadă de review).
4. Orice suprafață de răspuns trece prin recall-ul guvernat; etichetele epistemice vin din cod, nu din model.
5. Castingul pe naturi: nu antrena un model contra modului lui nativ — proiectează rolul în jurul naturii.

## 4. Starea la data handoff-ului

- **Master = `6cf92cb`** (merge PR #3): baseline canonic RB-1/C1; corespondența 000/001/001a în repo; toate notele review-ului meu închise de Sol în `44959bf`.
- **PR #4 DESCHIS** (`claude/idempotency-conflict`): `E_IDEMPOTENCY_CONFLICT` în inbox-ul de comenzi — `request_hash` pe `pmorg.command.inbox`, conflict la aceeași cheie + cerere diferită sau rând legacy fără hash; 4 teste noi. Suite la zi: `pmorg_core` 53/53, smoke `org-min` 25/25. **Așteaptă**: review-ul încrucișat al lui Sol (punct deschis: canonicalizarea `json sort_keys` vs RFC 8785) + merge-ul ownerului.
- **Mingea la Sol**: faza de implementare CPMORG pe baseline-ul canonic.
- **Coadă (opțional, la mandat)**: Gate E1 (operatorul Sol pe participanți scriptați); evaluarea conectorului Fireflies; promovarea ferestrei de context din conducta email (`channels/email/imap_bridge.py`) în schema grefierului + conducta de chatter.

## 5. Veghea (de repornit la FIECARE sesiune nouă)

Un monitor persistent local, poll la 5 minute, care anunță în sesiune:

- commit-uri noi pe `origin/master` (autor + subiect);
- orice mișcare pe orice PR: snapshot `gh pr list --state all --limit 20 --json number,state,updatedAt,title`, diff pe linii (prinde comentarii, review-uri, push-uri, schimbări de stare, PR-uri noi);
- numărul de comentarii pe Issue #16 din PMORG-Platform.

La eveniment: acționează per protocol (citește, verifică ancorele, răspunde pe PR/issue), nu doar consemna. Backstop independent de laptop: rutina cloud `sol-watch` (orară, gestionată la https://claude.ai/code/routines) — acționează singură per protocol, escaladează push către owner NUMAI pentru decizii de principiu; gardurile ei: fără merge, fără canon în afara `claude/*`+PR, commit direct pe master DOAR pentru `docs/correspondence/`.

## 6. Arbitrii (Definition of Done)

- `pmorg_core`: suita de teste Odoo (53 la data handoff-ului) — bază proaspătă, `-i pmorg_core --test-tags /pmorg_core`.
- Smoke 25 verificări × 3 profiluri: `runner/run_smoke.py` (bootstrap în `runner/README.md`).
- Longitudinal: `runner/run_longitudinal.py` (Gate D, 26/26 + S7 5/5 + S8 6/6).
- Extracție/rezoluție: benchmark-urile din `aipm/`; conducta email: `channels/email/` (9/9).
- Nimic nu intră în master fără suite verzi + review încrucișat; canonul normativ cere în plus ownerul.

## 7. Securitate și igienă

- Chei API / credențiale: **exclusiv în env-ul proceselor, niciodată în repo** (repo-ul e public!). Sursele de adevăr pentru accese: ownerul + anexa privată din PMORG-Platform.
- ADR-010: zero date/teste/credențiale de producție, oriunde.
- Infrastructura de test (sandboxuri, porturi, host-uri): în anexa privată, nu aici.
