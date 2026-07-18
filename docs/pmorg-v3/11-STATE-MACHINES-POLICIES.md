# PMORG v3 — state machines și politici baseline

| Câmp | Valoare |
|---|---|
| Status | Accepted |
| Baseline | `RB-1` |
| Contract version | `1.0` |
| Data | 2026-07-18 |

## 1. Reguli comune

- Stările tehnice sunt valori stabile și netraduse; etichetele UI pot fi
  traduse.
- Orice tranziție are actor, autoritate, versiune așteptată, correlation ID,
  causation ID și eveniment append-only.
- O tranziție invalidă este refuzată; nu este corectată implicit de LLM.
- Tranzițiile retry-uite cu aceeași cheie întorc același rezultat.
- Stage-ul Odoo configurabil nu înlocuiește starea de orchestration.
- Timpul care decide tranziții este server-side; în sandbox vine din
  `tick_id` trusted.

## 2. Inițiativa

### 2.1 Stări

```text
draft → clarifying → planned → awaiting_confirmation → active
                                                     ↓
                                                verifying → closed
```

`cancelled` este terminal și poate fi atins din orice stare ne-terminală
numai prin decizie autorizată. `closed` este terminal în RB-1; o nevoie nouă
produce o inițiativă legată prin `followup_of`, nu rescrierea celei închise.

### 2.2 Tranziții

| Din | În | Condiții minime |
|---|---|---|
| `draft` | `clarifying` | sursă, owner, companie și scop inițial identificabile |
| `clarifying` | `planned` | obiectiv, constrângeri și cel puțin un criteriu testabil |
| `planned` | `awaiting_confirmation` | plan versionat, taskuri propuse, responsabili și termene |
| `awaiting_confirmation` | `active` | toate confirmările cerute sunt obținute și înregistrate sau există excepții aprobate explicit |
| `active` | `clarifying` | informație materială lipsă; motiv și întrebare persistate |
| `active` | `planned` | replanificare necesară; se creează versiune nouă |
| `active` | `verifying` | munca cerută este completată și outcome candidate există |
| `verifying` | `active` | dovadă insuficientă, criteriu neîndeplinit sau remediere |
| `verifying` | `planned` | verificarea cere replanificare materială |
| `verifying` | `closed` | toate criteriile obligatorii verificate, approvals prezente și fără contradicție blocking |
| orice ne-terminală | `cancelled` | actor autorizat, motiv și impact consemnate |

## 3. Health flags ale inițiativei

Lifecycle state și sănătatea sunt separate. Pot exista simultan mai multe
flags:

| Flag | Condiție |
|---|---|
| `at_risk` | prag de risc depășit, dar execuția încă poate continua |
| `blocked` | progresul depinde de o condiție neîndeplinită |
| `paused` | pauză explicită autorizată; controller-ele nu inițiază acțiuni nepermise |
| `degraded` | o componentă necesară este indisponibilă ori registry-ul nu este valid |

UI-ul afișează prioritatea `paused > blocked > degraded > at_risk > healthy`,
dar ledgerul păstrează toate flags și motivele.

## 4. Task orchestration

### 4.1 Stări

```text
not_managed | ready | claimed | running | waiting_response
waiting_approval | scheduled | blocked | review | failed
completed | cancelled
```

`completed` descrie execuția PMORG, nu închide automat taskul business.
`memory_pending` și `delivery_pending` sunt condiții durabile de integrare
asociate taskului/outbox-ului, nu stări care suprascriu orchestration state.
După recovery, consumul idempotent golește condiția și taskul continuă din
starea persistentă anterioară.

### 4.2 Tranziții

| Din | În | Condiție/comandă |
|---|---|---|
| `not_managed` | `ready` | taskul intră sub politică PMORG |
| `ready` | `claimed` | claim atomic, eligibilitate și lease nou |
| `claimed` | `running` | run-ul prezintă lease token valid |
| `running` | `waiting_response` | mesaj livrat și wait condition persistată |
| `running` | `waiting_approval` | efectul cere approval |
| `running` | `scheduled` | următorul pas are `next_check_at` viitor |
| `running` | `blocked` | blocker explicit cu owner/condiție de ieșire |
| `running` | `review` | conflict, rezultat tardiv ori ambiguitate blocking |
| `running` | `completed` | execuția a produs rezultatul așteptat și receipt |
| orice activă | `failed` | eroare clasificată după epuizarea retry-urilor |
| `waiting_response` | `ready` | răspuns corelat sau timeout scadent |
| `waiting_approval` | `ready` | approval rezolvat |
| `scheduled` | `ready` | `next_check_at` scadent |
| `blocked` | `ready` | blocker rezolvat și reconciliat |
| `review` | `ready` | reviewerul autorizează reluarea |
| `review` | `completed` | reviewerul acceptă rezultatul existent |
| `failed` | `ready` | retry autorizat cu run nou |
| orice ne-terminală | `cancelled` | anulare autorizată; lease revocat |

Un task poate fi revendicat numai din `ready`. Expirarea lease-ului mută
`claimed`/`running` în `ready` sau `review` conform clasei de efect; nu
acceptă rezultatul tardiv în tăcere.

## 5. Run și lease

Un run este bounded și nu rămâne deschis pe durata așteptării umane. Stările
run-ului sunt:

```text
created → claimed → running → succeeded
                         ↘ failed
                         ↘ cancelled
                         ↘ expired
```

Când pasul produce `waiting_response`, `waiting_approval` sau `scheduled`,
run-ul persistă starea taskului și `next_check_at`, apoi devine `succeeded` și
eliberează lease-ul. Răspunsul ori tick-ul viitor mută taskul în `ready`, iar
un run nou îl revendică. Lease-ul există numai pe durata pasului activ; nu se
prelungește pe zile de așteptare umană.

Pentru profilul MVP:

- lease inițial: 5 minute virtuale;
- heartbeat recomandat: la maximum 60 secunde virtuale;
- maximum 3 încercări pentru erori retryable;
- backoff virtual: 1, 5 și 15 minute;
- efectele externe non-idempotente nu sunt retry-uite fără reconciliation;
- un run `expired` nu poate finaliza taskul fără review.

Aceste valori sunt configurație de profil, nu constante globale de produs.

## 6. Claim semantic

### 6.1 Stări

```text
proposed → under_review → validated → disputed → superseded
                 ↘ rejected                 ↘ expired
```

### 6.2 Reguli

| Tranziție | Condiții |
|---|---|
| `proposed → under_review` | evidence existentă, context și claim schema valide |
| `under_review → validated` | toate assessments obligatorii PASS și validator autorizat |
| `proposed/under_review → rejected` | probă invalidă, autoritate absentă sau contradicție fatală |
| `validated → disputed` | contradicție materială nouă ori contestare autorizată |
| `validated/disputed → superseded` | claim nou validat, scope și interval de înlocuire explicite |
| `validated → expired` | politica sau `valid_to` încheie valabilitatea fără înlocuitor |
| `disputed → validated` | contradicția este rezolvată în favoarea claim-ului, cu verdict nou |

Un claim `disputed` nu produce efect nou dacă politica acțiunii cere adevăr
necontestat. Statusurile `rejected`, `superseded` și `expired` nu șterg
evidence ori assessments.

## 7. Plan version

```text
draft → proposed → approved → superseded
                 ↘ rejected
draft/proposed → withdrawn
```

O versiune `approved` este imuabilă. Orice schimbare de task, responsabil,
termen material sau criteriu produce versiune nouă cu `base_version`.
`superseded` păstrează intervalul în care versiunea a fost activă.

## 8. Commitment

```text
proposed → awaiting_confirmation → confirmed → fulfilled
                                           ↘ breached → fulfilled_late
proposed/confirmed → cancelled | superseded
```

- `confirmed` cere evidence de la persoana responsabilă sau excepția aprobată;
- trecerea termenului mută commitment-ul neîndeplinit în `breached` la primul
  tick autoritativ;
- executarea după breach produce `fulfilled_late`, nu rescrie istoricul ca
  îndeplinire la timp;
- schimbarea responsabilului, termenului sau conținutului produce commitment
  nou și supersession;
- `cancelled` cere actor autorizat și motiv.

## 9. Contradiction

```text
open → under_review → resolved | dismissed
```

`resolved` păstrează verdictul, resolverul, evidence și efectul asupra
claims. `dismissed` înseamnă că relația propusă nu reprezenta o contradicție;
nu șterge claims. O contradicție blocking deschisă împiedică formalizarea sau
închiderea prevăzută de politică.

## 10. Approval

```text
pending → approved | rejected | expired | withdrawn | superseded
```

Reguli:

- numai `pending` poate fi rezolvat;
- actorul care a propus acțiunea nu poate aproba dacă politica cere four-eyes;
- `approved` este legat de command hash, scope și expiry; modificarea comenzii
  cere approval nou;
- un approval retry-uit cu aceeași cheie nu creează a doua rezoluție;
- expirarea nu este echivalentă cu respingerea;
- orice executare verifică approval-ul din nou server-side.

## 11. Outcome verification

```text
pending_evidence → ready_for_verification → under_review
                                      → verified
                                      → rejected
                                      → disputed
```

| Tranziție | Condiție |
|---|---|
| `pending_evidence → ready_for_verification` | toate tipurile obligatorii de dovadă sunt referite |
| `ready_for_verification → under_review` | politica cere judecată/validator uman |
| `ready_for_verification → verified` | criteriile complet mecanice trec și politica permite |
| `under_review → verified` | validator autorizat, fără conflict blocking |
| `under_review → rejected` | criteriu neîndeplinit sau dovadă invalidă |
| orice pre-verdict → disputed | dovezi incompatibile ori contestare autorizată |
| `disputed → under_review` | evidence suplimentară și reviewer asignat |

Inițiativa trece `verifying → closed` numai dacă toate outcomes obligatorii
sunt `verified`.

## 12. Niveluri de autonomie

| Nivel | Semantică |
|---|---|
| `read` | poate consulta în scope-ul ACL |
| `recommend` | poate formula o propunere fără efect extern |
| `execute_delegated` | poate executa numai clasa și limitele preaprobate |
| `approval_required` | creează approval request și așteaptă |
| `prohibited` | action/tool nu este expus și orice încercare este refuzată |

LLM-ul nu își alege nivelul. Odoo/policy engine îl rezolvă după organizație,
companie, action type, obiect, impact și actor.

## 13. Politica canonică `ORG-DIST-XNX-v1`

| Acțiune | Nivel/regulă |
|---|---|
| citire Project/HR/Inventory publicate | `read`, sub ACL |
| capturare evidence și claim proposal | `execute_delegated` |
| creare task de clarificare în inițiativa aprobată | `execute_delegated` |
| primul mesaj de clarificare | `execute_delegated` |
| un singur follow-up după 2 zile lucrătoare fără răspuns | `execute_delegated` |
| escaladare la owner după încă 3 zile lucrătoare | `execute_delegated`, template și destinatari fixați |
| plan nou ori schimbare de responsabil/termen material | `approval_required` |
| creare task operațional de reconciliere stoc | `approval_required` |
| modificare `stock.move`/`stock.picking` sau cantitate prin agent/runtime | `prohibited` în MVP; operarea umană Odoo rămâne permisă sub ACL |
| validare claim XNX | `approval_required`, validator diferit de autor |
| verificare outcome și închidere inițiativă | `approval_required` |

Praguri temporale XNX:

- `at_risk`: cu 2 zile lucrătoare înaintea termenului dacă outcome nu este
  `ready_for_verification`;
- `blocked`: imediat când o dependență obligatorie nu are owner ori termen;
- follow-up: la prima verificare după 2 zile lucrătoare complete;
- escaladare: la prima verificare după încă 3 zile lucrătoare;
- maximum un follow-up înaintea escaladării;
- ticks zilnice la 09:00 pentru controller-ele business și ticks tehnice
  separate pentru lease/retry.

## 14. Prioritatea regulilor

Într-un conflict se aplică, de la cea mai restrictivă:

```text
prohibited
> pauză de urgență / circuit breaker
> ACL și record rules Odoo
> approval_required
> policy de organizație/companie
> delegare explicită
> recomandarea agentului
```

Un nivel mai permisiv dintr-un strat inferior nu poate relaxa un strat
superior.

## 15. Evenimente obligatorii

Fiecare tranziție emite cel puțin:

```text
entity_type · entity_id · previous_state · new_state
state_version · actor · authority_ref · policy_version
correlation_id · causation_id · idempotency_key
effective_at · recorded_at · reason_code · evidence/receipt refs
```

Proiecțiile UI pot fi reconstruite din starea curentă și evenimentele
semnificative fără transcriptul LLM.
