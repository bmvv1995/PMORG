# PMORG — handoff pentru prima sesiune de implementare

| Câmp | Valoare |
|---|---|
| Status | Pregătit pentru execuție — suita v2 aprobată la 2026-07-16 |
| Data | 2026-07-16 |
| Obiectiv | Scheletul instalabil al aplicației și prima felie de date/teste |

## 1. Instrucțiunea de pornire

Citește integral, în această ordine:

1. `docs/pmorg-v2/00-PRODUCT.md`;
2. `docs/pmorg-v2/01-ARCHITECTURE.md`;
3. `docs/pmorg-v2/02-MVP.md`;
4. `docs/pmorg-v2/03-DECISIONS.md`;
5. acest document.

Aceste documente au precedență asupra README-ului și documentelor istorice
acolo unde descriu diferit arhitectura țintă. Documentele vechi rămân
evidența implementării și a raționamentului anterior; nu se rescriu pentru a
simula că v2 există deja.

## 2. Obiectivul unic al sesiunii

> Creează și verifică scheletul instalabil `pmorg_core`, cu
> modelele minime, extensia `project.task`, datele sintetice de bază și
> testele structurale. Nu implementa orchestrarea, memoria MCP sau AI-ul.

Sesiunea se oprește după ce această felie este instalabilă și testată. Nu
continuă automat spre runner, Hermes sau integrarea memoriei.

## 3. Preflight obligatoriu

- confirmă repo-ul, branch-ul și commitul de bază;
- verifică `git status` și păstrează orice schimbare existentă;
- verifică faptul că ADR-urile necesare din `03-DECISIONS.md` au statutul
  `Accepted`; dacă oricare este încă `Proposed`, oprește-te fără modificări și
  cere aprobarea explicită a suitei;
- folosește baseline-ul **Odoo 19 Community**, cu modulele `base`, `project`
  și `hr`; orice schimbare a baseline-ului necesită actualizarea documentelor
  de decizie înaintea codului;
- verifică modul concret de rulare a Odoo 19 Community și a testelor;
- verifică dacă există `project-protocol.json` și aplică protocolul dacă
  apare ulterior;
- nu folosi credențiale, baze sau servicii de producție;
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
```

Prima felie folosește un singur addon `pmorg_core`, dependent de `project` și
`hr`. Separarea ulterioară în addon-uri nu face parte din această sesiune.

## 5. Modelele și câmpurile primei felii

### `pmorg.initiative`

Minimul obligatoriu:

- identificator și nume;
- companie;
- owner;
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
- legătura cu participantul sintetic, dacă modelul ales o permite curat.

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

Fixture/demo separat de datele normale:

- companie: `Delta Distribution Test SRL`;
- Mara Ionescu — owner;
- Andrei Pop — manager operațional;
- Mihai Stan — gestionar;
- proiect: `Clarificări operaționale — TEST`;
- inițiativă: `XNX-001 — clarifică diferența raportată`;
- task: `Discută cu gestionarul despre incidentul XNX-001`;
- task rezultat: `Aplică acțiunea confirmată pentru XNX-001`.

Datele trebuie să se încarce numai explicit în mod demo/test și să nu conțină
adrese, telefoane, emailuri sau identificatori reali.

## 8. Testele obligatorii

1. addon-ul și dependențele sunt declarate corect;
2. inițiativa poate fi creată și legată de proiect;
3. taskurile pot fi legate de inițiativă;
4. tipurile de execuție sunt validate;
5. taskurile sintetice se încarcă repetabil;
6. compania și accesul de bază sunt respectate;
7. închiderea inițiativei fără datele minime cerute este refuzată, dacă
   această constrângere poate fi implementată complet în felia curentă;
8. instalarea nu creează date sintetice când demo/test este dezactivat.

Rulează testele Odoo reale dacă runtime-ul este disponibil. `git diff
--check` și importurile Python nu înlocuiesc testul de instalare.

## 9. Explicit interzis în această sesiune

- Hermes, `cc-bridge` sau modificarea Kanbanului vechi;
- MCP ori schimbarea serviciului `aipm`;
- LLM, prompturi sau fine-tuning;
- Telegram, Teams, email și Odoo Discuss automatizat;
- cron, scheduler, controller-e și timp virtual;
- claim, lease, heartbeat și retries;
- Inventory și Time Off anchor packs;
- migrarea datelor istorice;
- deploy, pilot, commit, push sau PR fără cerere separată;
- orice conexiune la producție.

## 10. Definition of Done al sesiunii

- structura addon-ului este clară și minimă;
- modelele și câmpurile de mai sus există;
- addon-ul se instalează efectiv într-o bază Odoo 19 Community de test;
- UI-ul minim este navigabil în acea bază;
- fixture-urile sintetice sunt separate și repetabile;
- testele disponibile sunt verzi;
- nu există integrare prematură cu componentele excluse;
- `git diff --check` este curat;
- raportul final distinge clar ce a fost testat de ce a fost doar inspectat.

## 11. Prompt recomandat pentru sesiunea nouă

> Lucrează în repo-ul PMORG. Citește integral `docs/pmorg-v2/` în ordinea din
> `04-NEXT-SESSION.md`. Verifică mai întâi că toate ADR-urile necesare sunt
> `Accepted`; dacă există vreunul `Proposed`, oprește-te fără modificări și
> cere aprobarea explicită. Tratează deciziile `Accepted` drept normative.
> Implementează numai obiectivul unic al primei sesiuni: scheletul instalabil
> al aplicației Odoo PMORG, modelele minime, extensia `project.task`, datele
> sintetice și testele structurale. Nu integra Hermes, memoria MCP, LLM-uri
> sau canale. Nu utiliza și nu conecta nimic din producție. Oprește-te la
> Definition of Done și raportează separat dovezile și blocajele.

## 12. Etapa care urmează, dar nu face parte din sesiune

După aprobarea primei felii se proiectează și testează contractele atomice
pentru claim/lease/idempotency, outbox/inbox și adaptorul de memorie. Runnerul
de scenarii apare abia după aceste contracte; Hermes apare după smoke testul
Odoo–memorie.
