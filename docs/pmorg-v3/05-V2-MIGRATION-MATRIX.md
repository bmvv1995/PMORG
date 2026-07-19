# PMORG v3 — matricea de migrare din v2

| Câmp | Valoare |
|---|---|
| Status | Clasificare Accepted; inventarul necesită revalidare la bootstrap |
| Versiune | `3.0-baseline.3` |
| Data | 2026-07-19 |

## 1. Regula de migrare

V3 nu pornește de la zero conceptual, dar nici nu continuă mecanic codul
existent:

> **Păstrăm intenția și invariantele; portăm comportamentele prin teste;
> rescriem modelele care nu pot exprima cerința v3; retragem componentele care
> creează două surse de adevăr.**

V2, SB2 și SB3 rămân read-only/reference până când un artefact este clasificat
și acceptat pentru portare. Niciun import de date de producție nu intră în
MVP.

### 1.1 Statutul exact al SB3

SB3 este **baseline-ul executabil de referință pentru migrarea V3**. Nu este
codebase-ul și nu este o implementare parțială a V3.

Din SB3 păstrăm ca input de migrare:

- scenariile longitudinale cu timp virtual, restart, tăcere, duplicate,
  contradicție, supersession, conflict optimist și recovery;
- runnerul determinist și contractele observabile pe care le demonstrează;
- worldgen, fixture-urile sintetice, oracle-ul și run bundle-ul;
- scenariul Inventory/XNX și testele de closed world;
- ceasul trusted `pmorg.clock.tick` și testele dual-mode din S5;
- conducta `channels/email/` ca șablon de adaptor (benchmark 9/9), nu ca
  alegere implicită a primului canal real;
- proprietățile testabile de lease, idempotency, provenance și audit.

SB3 nu decide schema Semantic Core, topologia bazelor, UI-ul, limitele
Turn Coordinator, integrarea Onyx ori forma finală a addon-urilor Odoo.
Acestea sunt guvernate de `RB-1/C2` și se implementează în repository-ul separat
`PMORG-Platform`.

Un test SB3 devine test V3 numai după ce:

1. este exprimat pe contractele și state machines V3;
2. nu depinde de internals sau stubs legacy;
3. rulează împotriva `PMORG-Platform`;
4. produce artefactele și verdictul cerute de G3-A–G3-F.

## 2. Matricea conceptuală

| Zonă v2 | Decizie v3 | Observație |
|---|---|---|
| definiția operatorului persistent | păstrăm | intenția produsului nu se schimbă |
| inițiativa ca unitate centrală | păstrăm | taskul rămâne mijloc, nu produsul |
| Odoo-first | păstrăm | rescriem doar forma „aplicație Odoo” |
| agnosticism organizațional | păstrăm și testăm | aceleași trei profiluri rămân obligatorii |
| `project.task` canonic | păstrăm | proiecția Onyx nu devine al doilea Kanban |
| `pmorg.identity` | păstrăm și extindem | adăugăm bindings către user Onyx și channel principals |
| anchor packs și capability registry | păstrăm și întărim | context obligatoriu la fiecare turn/tool call |
| evidence → claim → validare → formalizare | păstrăm | devine centrul pipeline-ului Onyx-PMORG |
| detectorul golului `pmorg.provenance.gap` | păstrăm și întărim | stare și controller determinist în addon/control-plane Odoo, receipts în Semantic Core, digest/rata de acoperire în Onyx-PMORG |
| memorie externă numai prin MCP | rescriem | API intern de domeniu + MCP extern standard |
| Semantic Core în același storage cu search | respingem | ledger autoritar separat de indexul reconstruibil |
| orchestrator persistent | reimplementăm prin contract | runner determinist în MVP; Hermes rămâne adaptor candidat |
| Communication Gateway | adaptăm | intră în Turn Admission înainte de orchestrator/runner; după privacy/evidence, același Turn Coordinator continuă din `AdmittedMessage` |
| comenzi Odoo înguste | păstrăm | fără ORM/SQL generic |
| outbox/inbox, lease, idempotency | păstrăm | condiții obligatorii de acceptare |
| UI PMORG în principal Odoo | rescriem | Onyx-PMORG devine workspace; Odoo rămâne formal/fallback |
| worldgen, oracle, corpus și scorer | păstrăm aproape integral | actualizăm SUT-ul și manifestul cu Onyx-PMORG |
| gate-urile v2 | adaptăm | fork-ul și longitudinalitatea intră explicit în MVP |

## 3. `aipm`: ce se păstrează

Se portează mai întâi ca proprietăți și teste:

- autor structural, niciodată ghicit din text;
- ingest ledger și idempotency;
- external/unresolved entity ca stare explicită;
- provenance și content hash;
- validare live în Odoo ca probă;
- anti-poison, duplicate/retry și receipts idempotente;
- jurnal append-only;
- testele golden de rezoluție și recall;
- refuzul scrierilor nepermise.

Acestea sunt rezultate cerute, nu obligația de a păstra aceleași clase ori
tabele.

## 4. `aipm`: ce se adaptează

- extraction produce `EvidenceEnvelope` și `ClaimProposal` distincte;
- resolution folosește registry-ul Odoo negociat, compania, ACL-ul și
  versiunea pack-ului;
- deduplicarea evidence este separată de deduplicarea claims;
- privacy și gateway ingestion intră în Turn Coordinator;
- review-ul uman se restrânge la vocabular/ancoră; interpretarea claim-urilor
  nu se portează ca UI/coadă;
- commitments/due/stale devin proiecții pentru Odoo, orchestrator și UI;
- receipt-ul specific chatter devine receipt generic, legat de efect;
- REST-ul existent devine API intern versionat și MCP standard extern.

## 5. `aipm`: ce se rescrie

Schema v2 nu poate fi schema Semantic Core v3 deoarece, în forma prototip:

- evidence și claim sunt prea apropiate sau amestecate;
- trust/validarea nu exprimă assessments, autoritate și validator;
- lipsesc scope-uri obligatorii organization/instance/company;
- lipsesc valid time și recorded time distincte;
- contradiction și supersession nu sunt relații complete;
- ancorele nu exprimă toate instance UUID, company, registry version,
  fingerprint și `observed_write_date`;
- tipurile de ancoră pot proveni din inventar static/fallback;
- identity mapping este prea legat de un canal concret;
- izolarea multi-organizație nu este demonstrată.

O regulă de forma „claim-ul este fact dacă un câmp Odoo îl susține live” nu
se portează. Citirea live este numai una dintre probe; factul cere și
proveniență, autoritate, timp și politica aplicabilă.

Se retrag din v3:

- UI-ul propriu `aipm`, înlocuit de workspace-ul Onyx-PMORG;
- sesiunile in-memory;
- wrappers LLM, embeddings și RAG generic proprii;
- inventarul static de tipuri;
- pollerul generic de chatter ca mecanism principal;
- regula legacy v1 „singura scriere este `message_post`”, deja superseded în
  v2 de ADR-006 prin comenzi business înguste; nu este comportament v2 de
  păstrat.

## 6. Odoo prototypes: portare controlată

Addon-urile prototip sunt surse de vocabular și scenarii, nu baseline de
producție. Se păstrează conceptual:

- lifecycle-ul inițiativei;
- separarea business state de orchestration state;
- tipurile de task PMORG;
- fixture-ul XNX;
- ideile de lease, idempotency, events și anchor packs care trec testele.

Se rescrie sau se completează înainte de portare:

- `pmorg_core` instalabil fără HR și Inventory;
- toate rolurile prin `pmorg.identity`;
- capability registry live, fără fallback static;
- anchor packs opționale și fingerprint-uri;
- API atomic, outbox/inbox, optimistic concurrency și ACL;
- ancore scoped pe instanță și companie;
- securitate și migration scripts incluse real în manifest.

Nicio componentă aflată numai într-un director untracked sau într-un sandbox
rsync nu devine sursă de release înainte să fie importată intenționat, cu
proveniență și teste.

## 7. Lecții concrete din sandboxurile existente

Aceste observații devin teste negative v3:

| Observație de prototip | Cerință v3 |
|---|---|
| Odoo și memoria au putut împărți același cluster/user | servicii/DB/roluri separate; Odoo nu scanează bazele memoriei |
| imagine Odoo nightly sau baseline mutabil | tag, digest și revizie fixate în run bundle |
| endpoint custom JSON-RPC numit MCP | MCP standard și test de interoperabilitate |
| registry cu tipuri statice/fallback | descriptor live publicat de Odoo și negociat fail-closed |
| ancoră verificată doar prin model + `res_id` | instanță, companie, ACL, registry și record version obligatorii |
| timeline bazat aproape numai pe `created_at` | valid time, recorded time și query `as_of` |
| contradicție declanșată manual | detecție, relație și rezoluție first-class |
| rezultatele evaluării nu sunt artefacte versionate | run bundle și report content-addressed obligatorii |

## 8. Componente legacy

| Componentă | Destinație |
|---|---|
| orice Kanban de orchestrator, inclusiv Hermes `kanban_*` | nu se portează ca registry; doar idei de scheduling/retry în adaptor |
| `components/cc-bridge` | se retrage; runtime-ul cognitiv este Onyx-PMORG |
| channel gateway | se adaptează la `MessageEnvelope` tranzitoriu, Turn Admission și `AdmittedMessage`; raw content nu traversează orchestratorul |
| privacy gate | se păstrează ca invariantă deterministă de ingestion |
| `pmorg.provenance.gap`, detector D1 și benchmark P/R | se portează în addon-ul Odoo ca state machine/controller determinist, folosind query-uri Semantic Core; nu se copiază granularitatea defectuoasă per-record |
| cron/digest | se transformă în controller + proiecție UI/message |
| receipts | se generalizează pentru evidence, delivery și efect Odoo |
| teste și fixtures utile | se portează înaintea codului pe care îl protejează |

## 9. Faze de migrare

1. înghețăm v2/SB2/SB3 și inventariem commiturile/artefactele;
2. transformăm invariantele selectate în teste independente de implementare;
3. bootstrapăm fork-ul Onyx și îi calificăm buildul upstream curat;
4. implementăm contextul, Semantic Core și Turn Coordinator;
5. rescriem addon-urile Odoo din specificație și teste;
6. portăm selectiv fixtures/worldgen și runnerul determinist;
7. atingem M0 și apoi G3-A–G3-F;
8. calificăm un adaptor de orchestrator pe contractul înghețat; Hermes rămâne opțiune;
9. evaluăm separat importul de date legacy; nu facem dual-write între
   Kanbanuri.

Maparea normativă a celor opt operații `pmorg-memory/1.0` la cele unsprezece
operații v3, a erorilor `MEM_*` și a idempotency este în
[14-V2-CONTRACT-SUPERSESSION](14-V2-CONTRACT-SUPERSESSION.md). Niciun test SB3
nu se portează prin aliasuri tăcute.

## 10. Definition of Done pentru migrare

Migrarea este completă numai când fiecare artefact v2 relevant are unul din
statusurile `ported`, `reimplemented`, `retired` sau `reference-only`, cu:

- owner și justificare;
- testele care îi păstrează comportamentul dorit;
- destinația v3;
- date/licență/proveniență clare;
- niciun proces activ dependent de două surse canonice.
