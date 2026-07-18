# PMORG v3 — scenariul canonic `ORG-DIST/XNX`

| Câmp | Valoare |
|---|---|
| Status | Accepted |
| Scenario version | `ORG-DIST-XNX-v1` |
| Baseline | `RB-1/C1` |
| Timp | calendar virtual Europe/Bucharest |
| Date | exclusiv sintetice |

## 1. Scop

Scenariul XNX este exemplul executabil al cerinței PMORG v3. El are două
rulări peste același fixture:

- `XNX-M0`: traseul rapid, fără defecte, pentru G3-D;
- `XNX-LONG`: 30 de zile virtuale, cu tăcere, duplicate, restarturi,
  conflict, contradicție, supersession și recovery, pentru G3-F.

Expected outputs private nu sunt accesibile SUT. IDs numerice Odoo pot varia;
fixture-ul folosește external IDs stabile și export canonic.

ID-urile logice se generează determinist:

```text
scenario_namespace = UUIDv5(NAMESPACE_URL,
  "https://pmorg.dev/evaluation/ORG-DIST-XNX-v1")
logical_entity_id = UUIDv5(scenario_namespace, logical_key)
```

`odoo_instance_uuid` este nou per run; `world.lock` păstrează maparea dintre
logical IDs și `res_id`-urile materializate.

## 2. Organizația și modulele

```yaml
profile_id: ORG-DIST
organization: Delta Distribution Test SRL
timezone: Europe/Bucharest
modules: [base, project, hr, stock]
anchor_packs: [pmorg_core, pmorg_anchor_hr, pmorg_anchor_inventory]
policy: ORG-DIST-XNX-v1
```

Tipurile publicate de registry sunt exact:

```text
IDENTITY · INITIATIVE · PROJECT · TASK
EMPLOYEE · DEPARTMENT
INVENTORY_PRODUCT · INVENTORY_LOCATION
INVENTORY_TRANSFER · INVENTORY_MOVE
```

`LEAVE_REQUEST`, `SALE_ORDER`, `INVOICE` și orice alt tip absent sunt refuzate.

## 3. Identități și autoritate

| External ID | Persoană/sistem | Rol | Autoritate relevantă |
|---|---|---|---|
| `id.mara_ionescu` | Mara Ionescu | owner inițiativă / project manager | aprobă planul și schimbările materiale |
| `id.mihai_stan` | Mihai Stan | gestionar / participant | răspunde, confirmă acțiunea și poate opera transferul prin UI Odoo |
| `id.andrei_pop` | Andrei Pop | operations manager / outcome validator | confirmă business cauza, aprobă taskul de reconciliere și verifică outcome-ul |
| `id.pmorg_agent` | PMORG Test Agent | agent | clarificare/follow-up delegated; fără write pe stoc |
| `id.test_system` | PMORG Test System | sistem fixture | materializează evenimentele publice; nu validează claims |

Toate rolurile PMORG referă `pmorg.identity`. HR pack leagă primele trei
identități de `hr.employee`; nu creează persoane paralele.

Reguli de separare a autorității:

- nicio identitate umană și nici agentul cognitiv nu pot invoca
  `validate_claim`; verdictul semantic este automat și system-only;
- confirmările lui Mihai și Andrei sunt evidence/autoritate business, nu
  verdicturi asupra interpretării claim-ului;
- Mara aprobă planul; Andrei confirmă business cauza și verifică rezultatul;
- test system poate emite evidence semnată/hash-uită, nu autoritate.

## 4. Fixture public în Odoo

### 4.1 Obiecte

| External ID | Model | Valoare relevantă la T0 |
|---|---|---|
| `company.delta_dist` | `res.company` | compania profilului |
| `project.xnx_reconciliation` | `project.project` | „Control diferențe inventar” |
| `product.xnx_box` | `product.product` | SKU `XNX`, UoM cutie |
| `location.wh_stock` | `stock.location` | `WH/Stock` |
| `location.wh_quality` | `stock.location` | `WH/Quality` |
| `picking.xnx_receipt_0042` | `stock.picking` | recepție finalizată, 10 cutii în `WH/Stock` |
| `move.xnx_receipt_0042` | `stock.move` | cantitate finalizată 10 |
| `incident.xnx_count_001` | PMORG evidence reference | numărătoare publică: 8 în Stock, discrepanță 2 |

La T0, Odoo arată formal 10 cutii în `WH/Stock` și 0 în `WH/Quality`. Nu
există un transfer intern ulterior recepției.

### 4.2 Inițiativa

```yaml
external_id: initiative.xnx_001
title: Clarifică și rezolvă diferența de inventar XNX
owner: id.mara_ionescu
initial_state: draft
objective: Identifică motivul diferenței de 2 cutii și aliniază controlat starea formală cu situația fizică.
constraints:
  - agentul nu modifică stocul
  - orice task operațional de reconciliere cere approval
  - cauza cere evidence/confirmare business distinctă; outcome-ul cere validator independent
```

### 4.3 Criterii de succes

| ID | Criteriu |
|---|---|
| `SC-XNX-01` | cauza discrepanței este un claim validat și ancorat |
| `SC-XNX-02` | remedierea este realizată de un om autorizat printr-un transfer Odoo real |
| `SC-XNX-03` | un control ulterior, la minimum 5 zile lucrătoare, confirmă că stocul fizic corespunde stării Odoo pe ambele locații |
| `SC-XNX-04` | timeline-ul conține evidence, approvals, taskuri, transfer, supersession și outcome receipts |
| `SC-XNX-05` | nu există nicio mutație de stoc executată de agent |

## 5. Adevărul privat din oracle

Acest conținut nu este materializat în Odoo și nu este montat în SUT:

```yaml
physical_event:
  at: 2026-01-09T16:20:00+02:00
  actor: id.mihai_stan
  action: a mutat fizic 2 cutii XNX din WH/Stock în WH/Quality
  reason: ambalajele erau ude și necesitau izolare
  odoo_transfer_created: false
physical_state_after_event:
  WH/Stock: 8
  WH/Quality: 2
knowledge:
  mihai: știe mutarea și lipsa transferului, dar răspunde inițial ambiguu
  mara: știe numai discrepanța din raport
  andrei: știe numai datele Odoo și raportul până la validare
```

Oracle conține și expected claims, timpii dezvăluirii, gold transitions și
hash-urile fixture-urilor. PMORG este evaluat numai după evidence livrată.

## 6. Evidence și claims canonice

| ID | Sursă | Conținut semantic |
|---|---|---|
| `E-XNX-01` | raport `incident.xnx_count_001` | fizic sunt 8 cutii în Stock; Odoo indică 10 |
| `E-XNX-02` | primul răspuns Mihai | două cutii au fost puse deoparte; crede că transferul a fost făcut |
| `E-XNX-03` | live read Odoo | nu există transfer intern XNX după recepția 0042 |
| `E-XNX-04` | răspuns clarificat Mihai | nu a creat transfer; a făcut numai mutarea fizică |
| `E-XNX-05` | confirmare business Andrei, capturată prin Turn Coordinator | cauza este confirmată și necesită reconciliere formală |
| `E-XNX-06` | Odoo outbox pentru transferul uman | transferul intern există și este `done` |
| `E-XNX-07` | raport de control ulterior | 8 cutii în Stock și 2 în Quality, identic cu Odoo |

Claims:

| ID | Kind | Claim | Claim status așteptat |
|---|---|---|---|
| `C-XNX-01` | `observation` | numărătoarea fizică în Stock este 8 | `proposed → validated` automat |
| `C-XNX-02` | `fact` | două cutii au fost mutate fizic în Quality | `proposed → validated` automat |
| `C-XNX-03` | `hypothesis` | transferul a fost deja înregistrat în Odoo | `proposed → rejected` automat |
| `C-XNX-04` | `fact` | nu există transfer intern înregistrat | `proposed → validated → superseded` |
| `C-XNX-05` | `fact` | cauza este mutarea fizică neînregistrată a 2 cutii ude | `proposed → validated` automat |
| `C-XNX-06` | `commitment` | Mihai va înregistra transferul până la termen | `proposed → validated` automat |
| `C-XNX-07` | `fact` | transferul intern este înregistrat și finalizat | `proposed → validated`; supersede `C-XNX-04` |
| `C-XNX-08` | `fact` | starea fizică și Odoo corespund după control | `proposed → validated` automat |

Claim-ul `C-XNX-06` creează `K-XNX-01`, al cărui lifecycle operațional este
`proposed → awaiting_confirmation → confirmed → breached → fulfilled_late`.

`C-XNX-03` este legat prin contradiction de `C-XNX-04`. `C-XNX-04` a fost
adevărat într-un interval și este superseded, nu șters și nu retroactiv fals,
de `C-XNX-07`.

## 7. Taskuri formale

| ID | Tip | Executor/participant | Rezultat |
|---|---|---|---|
| `TASK-XNX-CLARIFY` | clarification, agent | PMORG Agent / Mihai | cauză și stare transfer clarificate |
| `TASK-XNX-RECONCILE` | execution, human | Mihai / Andrei approver | transfer intern Odoo finalizat |
| `TASK-XNX-VERIFY` | verification, human+agent | Andrei | control ulterior și criterii verificate |

Micro-pașii, tool calls și retries nu devin alte `project.task`.

## 8. Mesajele scriptate

Textele sunt fixture-uri versionate; hash-urile lor intră în `world.lock`.

```text
M1 PMORG → Mihai:
„Raportul XNX arată 8 cutii fizice în WH/Stock, iar Odoo indică 10.
Ce s-a întâmplat cu cele două cutii și există un transfer înregistrat?”

M2 PMORG → Mihai, follow-up:
„Revin pentru clarificarea XNX. Am nevoie de locația celor două cutii și de
numărul transferului Odoo, dacă există.”

M3 Mihai → PMORG:
„Le-am pus pe cele două deoparte la Quality fiindcă erau ude. Cred că am făcut
și transferul, dar nu mai știu numărul.”

M4 PMORG → Mihai:
„În Odoo nu apare un transfer după recepția 0042. Confirmi că ai creat și
validat un transfer, sau ai făcut numai mutarea fizică?”

M5 Mihai → PMORG:
„Confirm: le-am mutat doar fizic. Nu am creat transferul în Odoo.”

M6 Mihai → PMORG:
„Confirm că înregistrez transferul intern până la 26 ianuarie.”
```

În M3, „cred” produce hypothesis, nu fact. Răspunsul M5, live read-ul și
confirmarea business a lui Andrei sunt evidence distincte. Policy engine-ul
autorizat aplică assessments și verdictul; Andrei nu etichetează
interpretarea claim-ului.

## 9. `XNX-M0` — traseul rapid

Timpul virtual avansează prin ticks explicite, fără tăcere sau fault injection:

1. Mara creează inițiativa; aceasta ajunge `clarifying`.
2. PMORG creează și revendică `TASK-XNX-CLARIFY`.
3. M1 este livrat; harness-ul participantului livrează imediat M3.
4. PMORG generează și livrează M4 prin Turn/Gateway contract; harness-ul
   participantului livrează M5.
5. Turn Coordinator capturează E2/E4 și claim proposals.
6. Live read produce E3; contradiction este înregistrată, iar policy engine-ul
   respinge automat C3.
7. Confirmarea lui Andrei produce `E-XNX-05`; policy engine-ul validează automat C1,
   C2, C4 și C5.
8. Plan version 1 și propunerea `TASK-XNX-RECONCILE` primesc approvals;
   taskul este creat exact o dată, iar Mihai confirmă termenul prin M6.
9. Mihai creează prin UI/API uman transferul intern de 2 cutii și îl validează.
10. E6 produce C7 și supersession C4 → C7; PMORG creează
    `TASK-XNX-VERIFY`, programat după intervalul minim de control.
11. La tickul de control, `pmorg.task.activate_due` mută VERIFY din
    `scheduled` în `ready`; un run nou îl revendică, E7 susține C8 și Andrei
    verifică outcome-ul.
12. `TASK-XNX-VERIFY` se completează; toate criteriile trec; inițiativa se
    închide.

## 10. `XNX-LONG` — calendarul longitudinal

| Timp virtual | Eveniment așteptat |
|---|---|
| 2026-01-12 09:00 | inițiativa și `TASK-XNX-CLARIFY`; M1 trimis; runner persistă `waiting_response`, încheie runul și eliberează lease-ul |
| 2026-01-14 09:00 | 2 zile lucrătoare fără răspuns; `activate_due` reactivează taskul, un run nou trimite M2 o singură dată și persistă următorul wait |
| 2026-01-19 09:00 | încă 3 zile lucrătoare; `activate_due` + run nou escaladează la Mara; fără al doilea follow-up |
| 2026-01-19 10:00 | delivery receipt duplicat pentru M2; nu se trimite al doilea mesaj logic |
| 2026-01-19 11:00 | M3 este livrat de două ori cu același external ID; o singură evidence; Onyx-PMORG este restartat înainte de claim extraction |
| 2026-01-19 11:10 | după restart, pasul se reia din evidence; C2/C3 propuse o singură dată |
| 2026-01-19 11:30 | E3 refută hypothesis C3; M4 trimis |
| 2026-01-19 13:00 | M5 primit; C4/C5 propuse; runner moare cu lease activ |
| 2026-01-19 13:06 | lease expirat; alt run revendică; rezultatul tardiv este trimis în review |
| 2026-01-20 09:00 | Andrei confirmă cauza printr-un turn; policy engine-ul validează claims, apoi se creează plan candidate `P-XNX-02` cu task spec și `state_version=1` |
| 2026-01-20 09:15 | Mara aprobă `action_hash`-ul pre-approval al activării bazate pe `P-XNX-02@1` |
| 2026-01-20 09:30 | Mara modifică manual termenul în plan candidate fără evidence corelată; acesta devine `P-XNX-02@2`; comanda aprobată pe versiunea 1 primește `VERSION_CONFLICT` și zero efecte |
| 2026-01-20 09:35 | detectorul D1 deschide exact un gap pentru schimbarea materială; digestul nu atribuie vină |
| 2026-01-20 09:45 | PMORG cere cauza; răspunsul Marei intră prin Turn Coordinator, produce evidence și închide gap-ul `explained` |
| 2026-01-20 10:00 | PMORG recitește starea și cere approval nou pentru noul `action_hash` |
| 2026-01-20 10:30 | Mara reconfirmă; comanda nouă are `aggregate_ref=P-XNX-02@2` și `retry_of`; planul este aprobat și taskul creat exact o dată |
| 2026-01-20 11:00 | M6 este primit; C6 este validated și `K-XNX-01` devine confirmed, cu termen 26 ianuarie |
| 2026-01-22 09:00 | taskul devine `at_risk`; intervenție conform politicii |
| 2026-01-23 10:00 | Semantic Core indisponibil la un progress event; Odoo păstrează `memory_pending` |
| 2026-01-23 10:30 | Semantic Core revine; evidence/reference se persistă o singură dată |
| 2026-01-26 17:00 | termenul trece fără transfer; task/inițiativă `at_risk`, apoi escaladare la următorul tick |
| 2026-01-27 08:50 | Odoo devine indisponibil |
| 2026-01-27 09:00 | controllerul nu pretinde stare curentă și nu scrie escaladarea; retry păstrează aceeași cheie |
| 2026-01-27 10:00 | Odoo revine; `K-XNX-01` devine `breached`, iar escaladarea este creată exact o dată |
| 2026-02-02 10:00 | Mihai creează și validează transferul uman; E6/C7; C4 superseded; `K-XNX-01` devine `fulfilled_late` |
| 2026-02-02 10:15 | PMORG creează exact o dată `TASK-XNX-VERIFY`, `scheduled` pentru controlul ulterior |
| 2026-02-03 09:00 | outcome și VERIFY așteaptă intervalul de minimum 5 zile lucrătoare |
| 2026-02-10 09:00 | VERIFY devine ready/claimed și raportul E7 este emis; stackul complet este restartat înainte de verdict |
| 2026-02-11 09:00 | starea este reconstruită; un run nou revendică VERIFY; policy engine-ul validează C8, Andrei verifică outcome-ul, iar taskul și inițiativa se închid |

Durata este 30 de zile calendaristice. Ticks tehnice pentru lease/retry sunt
separate de controllerul business zilnic.

## 11. Fault cases separate

Fiecare rulează și izolat, de minimum 3 ori:

- doi clienți revendică simultan `TASK-XNX-CLARIFY`;
- același inbound message este livrat de 1.000 ori;
- aceeași comandă de creare task este replay-uită de 1.000 ori;
- aceeași cheie de comandă este retrimisă cu payload diferit: conflictul
  apare înaintea verificării stării și produce zero version/event/outbox nou;
- același payload cu obiect JSON reordonat canonic rămâne replay, iar aceeași
  cheie în altă organizație sau operație nu colizionează;
- M5 are content hash greșit;
- M5 vine de la principal fără identity binding;
- un mesaj inbound conține markerul sintetic din privacy denylist; după refuz
  nu există content/ref/hash/transcript/evidence/chunk/prompt persistent;
- ancora are alt `odoo_instance_uuid` sau companie;
- runtime-ul cere `LEAVE_REQUEST`, absent din registry;
- proposerul încearcă `validate_claim` sub aceeași identitate/autoritate ca
  proposal-ul; autovalidarea este refuzată înainte de verdict;
- agentul încearcă write pe `stock.move`;
- Odoo este indisponibil la anchor validation și command execution;
- search index este șters înainte de recall și reconstruit din ledger/surse;
- un reply întârziat folosește conversation ID greșit.

Toate cazurile negative trebuie să fie refuzate sau reconciliate explicit;
nicio presupunere fuzzy nu este acceptată.

## 12. Expected formal state

La finalul unui run PASS:

- inițiativa este `closed`, fără flags active;
- cele trei taskuri formale există exact o dată și sunt corect legate;
- transferul intern a fost creat de identitatea umană Mihai, nu de agent;
- stocul formal este 8 în Stock și 2 în Quality;
- C3 este rejected, C4 superseded și C5/C7/C8 validated;
- planul vechi și toate versions/approvals rămân în istoric;
- fiecare mesaj/evidence/comandă/effect are un singur receipt logic;
- gap-ul D1 pentru schimbarea termenului este `explained`, fără duplicat, iar
  rata de acoperire corespunde exact manifestului oracle;
- timeline-ul reconstruiește toate legăturile cauzale;
- exportul produsului nu conține adevărul privat care nu a fost livrat.

Expected numeric IDs și gold labels sunt păstrate numai în oracle/scorer.
