# PMORG — handoff pentru prima sesiune de implementare

| Câmp | Valoare |
|---|---|
| Status | Pregătit pentru execuție — ADR-urile necesare S1 sunt Accepted |
| Versiune suită | 0.3 |
| Data | 2026-07-17 |
| Obiectiv | Nucleul instalabil, fără dependențe de domeniu, și profilul minimal |

## 1. Instrucțiunea de pornire

Citește integral, în această ordine:

1. `docs/pmorg-v2/00-PRODUCT.md`;
2. `docs/pmorg-v2/01-ARCHITECTURE.md`;
3. `docs/pmorg-v2/02-MVP.md`;
4. `docs/pmorg-v2/03-DECISIONS.md`;
5. `docs/pmorg-v2/05-MEMORY-DATA.md`;
6. `docs/pmorg-v2/06-EVALUATION-SANDBOX.md`;
7. acest document.

Aceste documente au precedență asupra README-ului și documentelor istorice
acolo unde descriu diferit arhitectura țintă. Documentele vechi rămân
evidența implementării și a raționamentului anterior; nu se rescriu pentru a
simula că v2 există deja.

## 2. Obiectivul unic al sesiunii

> Creează și verifică scheletul instalabil `pmorg_core`, cu
> modelele minime, extensia `project.task`, profilul sintetic minimal și
> testele structurale. Nucleul trebuie să funcționeze fără HR, Inventory sau
> Time Off. Nu implementa orchestrarea, memoria MCP sau AI-ul.

Sesiunea se oprește după ce această felie este instalabilă și testată. Nu
continuă automat spre runner, Hermes sau integrarea memoriei.

## 3. Preflight obligatoriu

- confirmă repo-ul, branch-ul și commitul de bază;
- verifică `git status` și păstrează orice schimbare existentă;
- verifică faptul că ADR-001, ADR-002, ADR-003, ADR-010, ADR-011, ADR-013 și
  ADR-014 din `03-DECISIONS.md` au statutul `Accepted`; acestea sunt deciziile
  necesare S1. Dacă oricare este încă `Proposed`, oprește-te fără modificări
  și cere aprobarea explicită. ADR-015–018 nu blochează S1; devin obligatorii
  numai înaintea etapelor de evaluare pe care le guvernează;
- folosește baseline-ul **Odoo 19 Community**, cu modulele `base` și
  `project`, la revizia `1b8f6802832cfa4d146193a912af1f4445d09f0a`; baza testului minimal nu instalează
  `hr`, `stock` sau Time Off; dacă se construiește o imagine, consemnează
  digestul și lock-ul dependențelor; orice schimbare a baseline-ului necesită
  actualizarea documentelor de decizie înaintea codului;
- verifică modul concret de rulare a Odoo 19 Community și a testelor;
- verifică dacă există `project-protocol.json` și aplică protocolul dacă
  apare ulterior;
- nu folosi credențiale, baze sau servicii de producție;
- orice endpoint/DB/instance UUID de test trebuie declarat explicit și
  verificat fail-closed; un default de producție invalidează preflightul;
- nu descărca și nu importa date reale.

Dacă runtime-ul Odoo 19 Community de test nu este disponibil, poate fi
pregătită structura și poate fi documentat blocajul, dar obiectivul sesiunii
și Definition of Done rămân neatinse.

## 4. Structura țintă inițială

Locul implicit este:

```text
odoo_addons/
  pmorg_core/
    __init__.py
    __manifest__.py
    models/
    security/
    views/
    data/
    tests/
evaluation/
  profiles/
    org-min.yaml
```

Orice substrat S0 existent este numai infrastructură de referință, nu sursa
canonică a addon-ului și nu Gate A. Codul nou trăiește în `odoo_addons/`, iar
orice deploy îl consumă fără a păstra o copie divergentă.

Prima felie folosește un singur addon `pmorg_core`, dependent numai de `base`
și `project`. Nu importă, nu moștenește și nu declară relații către
`hr.employee`, `stock.*`, `hr.leave` sau alte modele opționale. Anchor
pack-urile de domeniu apar în sesiuni ulterioare.

`evaluation/profiles/org-min.yaml` este manifest de date/configurație inclus în
același build, nu un manifest alternativ de addon. El declară cel puțin
`profile_id`, revizia Odoo fixată, modulele `base`/`project`, lista goală de
pack-uri opționale și referințele către politici/fixture-uri. Celelalte două
profiluri îl vor completa ulterior prin fișiere de configurație paralele,
fără schimbarea `pmorg_core/__manifest__.py`.

## 5. Modelele și câmpurile primei felii

### `pmorg.identity`

Minimul obligatoriu:

- `company_id`;
- `partner_id` obligatoriu;
- `user_id` opțional;
- `identity_kind`: `human`, `agent` sau `system`;
- unicitate pe `(company_id, partner_id)`;
- constrângere ca `user_id.partner_id` să coincidă cu `partner_id`.

Ownerii, validatorii și participanții PMORG referă exclusiv acest model. Nu
introduce câmpuri alternative care să permită alegerea între partner, user și
employee.

### `pmorg.initiative`

Minimul obligatoriu:

- identificator și nume;
- companie;
- `owner_identity_id`;
- descriere/context;
- obiectiv;
- stare lifecycle;
- data creării și audit Odoo;
- relație cu proiectul și taskurile.

Stările inițiale:

```text
draft | clarifying | planned | awaiting_confirmation | active |
verifying | closed | cancelled
```

Nu implementa încă întreaga mașină de tranziții. Adaugă numai constrângerile
structurale care pot fi demonstrate corect în această sesiune.

### Extensia `project.task`

Minimul obligatoriu:

- `pmorg_initiative_id`;
- tipul PMORG al taskului;
- `execution_mode`;
- rezultatul așteptat;
- starea de orchestrare inițială;
- `next_check_at`;
- starea verificării;
- legătura cu participantul prin `pmorg.identity`, fără dependență de
  `hr.employee`.

Nu implementa încă claim, lease, heartbeat, API-ul runtime sau controller-ele.
Câmpurile lor se adaugă după înghețarea contractului din etapa următoare.

## 6. UI minim

- meniu PMORG;
- listă și formular pentru inițiative;
- legătură vizibilă inițiativă–proiect–taskuri;
- câmpurile PMORG vizibile pe formularul taskului;
- filtru pentru taskuri umane, agentice, hibride și de monitorizare.

Nu construi dashboard, timeline complex, memorie UI sau design custom Owl în
această sesiune.

## 7. Date sintetice

Fixture/demo separat de datele normale, pentru profilul `ORG-MIN`:

- companie: `Atelier Minimal Test SRL`;
- Ana Dobre — owner;
- Paul Rusu — validator autorizat;
- Victor Neagu — participant;
- fiecare are `pmorg.identity` peste `res.partner`, cu `user_id` numai unde
  acțiunea în Odoo îl cere; nu există angajați;
- proiect: `Coordonare internă — TEST`;
- inițiativă: `MIN-001 — clarifică criteriul de acceptare`;
- task: `Obține criteriul de acceptare lipsă`;
- task rezultat: `Finalizează livrabilul conform criteriului confirmat`.

Datele trebuie să se încarce numai explicit în mod demo/test și să nu conțină
adrese, telefoane, emailuri sau identificatori reali.

## 8. Testele obligatorii

1. addon-ul declară numai dependențele `base` și `project`;
2. addon-ul se instalează într-o bază fără `hr`, `stock` și Time Off;
3. modelele și view-urile nu conțin referințe directe la modele opționale;
4. identitatea impune unicitatea și consistența partner–user;
5. ownerul și participantul sunt referiți numai prin `pmorg.identity`;
6. inițiativa poate fi creată și legată de proiect;
7. taskurile pot fi legate de inițiativă;
8. tipurile de execuție sunt validate;
9. taskurile sintetice se încarcă repetabil;
10. manifestul `org-min.yaml` fixează baseline-ul și selectează numai
    capabilitățile permise profilului minimal;
11. compania și accesul de bază sunt respectate;
12. închiderea inițiativei fără datele minime cerute este refuzată, dacă
   această constrângere poate fi implementată complet în felia curentă;
13. instalarea nu creează date sintetice când demo/test este dezactivat.

Rulează testele Odoo reale dacă runtime-ul este disponibil. `git diff
--check` și importurile Python nu înlocuiesc testul de instalare.

## 9. Explicit interzis în această sesiune

- Hermes, `cc-bridge` sau modificarea Kanbanului vechi;
- MCP ori schimbarea serviciului `aipm`;
- LLM, prompturi sau fine-tuning;
- Telegram, Teams, email și Odoo Discuss automatizat;
- cron, scheduler, controller-e și timp virtual;
- claim, lease, heartbeat și retries;
- HR, Inventory și Time Off anchor packs;
- cod condițional, `__manifest__.py`, build sau feature flag alternativ per
  organizație; manifestele comune de date/configurație din
  `evaluation/profiles/` sunt permise și obligatorii;
- migrarea datelor istorice;
- deploy, pilot, commit, push sau PR fără cerere separată;
- orice conexiune la producție.

## 10. Definition of Done al sesiunii

- structura addon-ului este clară și minimă;
- modelele și câmpurile de mai sus există;
- addon-ul se instalează efectiv într-o bază Odoo 19 Community cu `project`,
  fără `hr`, `stock` și Time Off;
- UI-ul minim este navigabil în acea bază;
- fixture-urile sintetice sunt separate și repetabile;
- manifestul `org-min.yaml` descrie profilul fără a modifica buildul;
- testele disponibile sunt verzi;
- nu există integrare prematură cu componentele excluse;
- `git diff --check` este curat;
- raportul final distinge clar ce a fost testat de ce a fost doar inspectat.

## 11. Prompt recomandat pentru sesiunea nouă

> Lucrează în repo-ul PMORG. Citește integral `docs/pmorg-v2/` în ordinea din
> `04-NEXT-SESSION.md`. Verifică mai întâi că ADR-001, ADR-002, ADR-003,
> ADR-010, ADR-011, ADR-013 și ADR-014 sunt `Accepted`; dacă unul este
> `Proposed`, oprește-te fără modificări și cere aprobarea explicită.
> ADR-015–018 nu blochează S1. Tratează deciziile `Accepted` drept normative.
> Implementează numai obiectivul unic al primei sesiuni: scheletul instalabil
> al aplicației Odoo PMORG, modelele minime, extensia `project.task`, profilul
> minimal și testele structurale. Implementează identitatea canonică
> `pmorg.identity`; ownerii și participanții nu au câmpuri alternative către
> user/partner/employee. `pmorg_core` depinde numai de `base` și `project`; nu
> instala și nu referi HR, Inventory sau Time Off. Nu integra Hermes, memoria
> MCP, LLM-uri sau canale. Nu utiliza și nu conecta nimic din producție.
> Oprește-te la Definition of Done și raportează separat dovezile și
> blocajele.

## 12. Etapa care urmează, dar nu face parte din sesiune

După aprobarea primei felii se îngheață contractele atomice pentru
claim/lease/idempotency și outbox/inbox și se construiește kernelul de
evaluare din etapa S2: manifest, oracle separat, ceas, recorder și scorer
minim, până la închiderea Gate A. Urmează anchor pack-urile HR/Inventory și
adaptorul de memorie.
Harness-ul pornește cele trei baze din același build; aceasta este precondiția
structurală a Gate C2, nu Gate C2 complet. Runnerul conversațional apare abia
după contracte și memorie; Hermes apare după smoke testul Odoo–memorie.
