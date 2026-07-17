# PMORG — contractele orchestrator ↔ Odoo (v1.0)

| Câmp | Valoare |
|---|---|
| Status | Înghețat v1.0 (2026-07-17, sub mandat delegat) |
| Versiune contract | `1.0` |
| Data | 2026-07-16 |
| Domeniu | Suprafața de comenzi, anvelopa, stările de orchestrare, outbox/inbox, erori |
| Sursă normativă | [01-ARCHITECTURE](01-ARCHITECTURE.md) §5, §9; ADR-006, ADR-007 |

Contractul definește **exact** ce poate cere runtime-ul (runner determinist,
ulterior Hermes) de la Odoo. Nicio altă scriere nu este disponibilă
runtime-ului (fail-closed, ADR-006). Schimbările incompatibile cer versiune
nouă de contract; adăugirile compatibile incrementează minor.

## 1. Transport și autentificare

- Transport MVP: RPC-ul standard Odoo (`/jsonrpc`, `execute_kw`) către modelul
  de serviciu **`pmorg.orchestrator.api`**, cu un cont de serviciu dedicat,
  fără drepturi de administrare.
- Fiecare comandă = o metodă `api_<nume>(payload: dict) -> dict`.
- ACL-urile, record rules și compania utilizatorului de serviciu se aplică
  nealterat; API-ul nu folosește `sudo` pentru efecte business.

## 2. Anvelopa comenzii

Toate comenzile primesc un singur `payload` JSON:

```json
{
  "schema_version": "1.0",
  "message_id": "uuid — unic per mesaj transmis",
  "correlation_id": "uuid — firul logic (ex. inițiativa/conversația)",
  "causation_id": "uuid sau null — mesajul care a cauzat comanda",
  "idempotency_key": "cheie unică în scope-ul sursei",
  "actor": {"type": "agent|user|system", "id": "identificator stabil"},
  "occurred_at": "RFC3339",
  "company_id": 1,
  "params": {}
}
```

Reguli:

1. `schema_version` diferit la major ⇒ `E_SCHEMA`.
2. `idempotency_key` lipsă la comenzi mutante ⇒ `E_SCHEMA`.
3. Rejucarea aceleiași `(actor.id, idempotency_key)` întoarce **răspunsul
   original memorat** din `pmorg.command.inbox`, fără efect nou.
4. `actor` este identitatea tehnică; autoritatea se evaluează per comandă.
5. Orice referință la o persoană sau un agent din `params` folosește ID-uri
   `pmorg.identity` (ADR-014), niciodată partner/user/employee direct.

## 3. Răspunsul

```json
{
  "status": "ok | replay | error",
  "error": {"code": "E_*", "message": "…"} ,
  "result": {},
  "state_version": 4,
  "message_id": "ecoul message_id primit"
}
```

`replay` semnalează explicit un răspuns servit din inbox (idempotency).

## 4. Codurile de eroare

| Cod | Semnificație |
|---|---|
| `E_SCHEMA` | payload invalid sau versiune incompatibilă |
| `E_AUTH` | actor necunoscut sau neautentificat |
| `E_AUTONOMY` | politica de autonomie interzice acțiunea |
| `E_COMPANY` | compania nu corespunde înregistrării |
| `E_UNKNOWN` | task/run/înregistrare inexistentă |
| `E_STATE` | tranziție de orchestrare invalidă |
| `E_VERSION` | `expected_version` nu mai corespunde (conflict optimist) |
| `E_LEASE_HELD` | există lease valid al altui owner |
| `E_LEASE` | token de lease invalid sau expirat |
| `E_NOT_DUE` | taskul nu este eligibil/scadent pentru claim |
| `E_CRITERIA` | închidere/completare fără criteriile sau dovezile cerute |

## 5. Stările de orchestrare și tranzițiile

Stările (`project.task.orchestration_state`) sunt cele din
[01-ARCHITECTURE](01-ARCHITECTURE.md) §4.1. Tranzițiile permise prin API:

| Din | În | Comanda |
|---|---|---|
| `not_managed` | `ready` | `mark_managed` (sau `propose_task` la creare) |
| `ready`, `scheduled` (scadent) | `claimed` | `claim_task` |
| `claimed` | `running` | `record_progress` (primul progres) |
| `running` | `waiting_response` | `record_waiting_response` |
| `waiting_response` | `running` | `record_progress` (răspuns corelat) |
| `claimed`, `running`, `waiting_response` | `scheduled` | `schedule_next_check` (+ eliberare lease) |
| `claimed`, `running`, `waiting_response` | `blocked` | `block_task` |
| `blocked` | `ready` | `release_task(reason="unblocked")` |
| `claimed`, `running` | `ready` | `release_task` |
| `running` | `review` | `complete_run(outcome="needs_review")` |
| `running`, `review` | `completed` | `complete_run` / validare conform politicii |
| `running` | `failed` | `complete_run(outcome="failed")` |
| orice, lease expirat | `ready` | watchdog determinist (`reclaim_expired`) |

Invariante:

- starea business (stage Odoo) NU se schimbă prin aceste comenzi;
- `completed` pe orchestrare nu închide taskul business (ADR-003);
- orice tranziție incrementează `state_version` și scrie `pmorg.task.event`
  append-only + `pmorg.outbox.event`.

## 6. Claim și lease

`claim_task` reușește numai dacă, într-o **singură tranzacție cu row lock**
(`SELECT … FOR UPDATE`): taskul e `ready` sau `scheduled` cu
`next_check_at <= now`; nu există lease valid; compania corespunde;
`expected_version` (dacă e transmis) corespunde. Efectele atomice:

- se creează `pmorg.task.run` activ (actor, început, lease);
- `lease_token` opac (UUID) + `lease_expires_at = now + lease_seconds`
  (implicit 300s, maxim 3600s);
- `state_version += 1`, eveniment + outbox.

`heartbeat` extinde lease-ul doar pentru ownerul curent (`E_LEASE` altfel).
`reclaim_expired(now)` — determinist, idempotent — trece run-urile cu lease
expirat în `failed(reason="lease_expired")` și taskul în `ready`. Un
`complete_run` sosit după expirare ⇒ `E_LEASE`; rezultatul tardiv se
consemnează ca eveniment, nu ca efect.

## 7. Suprafața de comenzi v1.0

Read-only:

| Comanda | `params` | `result` |
|---|---|---|
| `list_due_work` | `now` (RFC3339, ceasul runnerului), `filters` opțional (`initiative_id`, `execution_mode`, `limit`) | listă de taskuri scadente: id, nume, tip, mod, stare, `next_check_at`, `state_version`, inițiativă |
| `get_task_state` | `task_id` | starea completă de orchestrare + run activ |

Mutante (toate cer anvelopa completă):

| Comanda | `params` esențiale | Semantica |
|---|---|---|
| `mark_managed` | `task_id` | `not_managed → ready` |
| `claim_task` | `task_id`, `lease_seconds?`, `expected_version?`, `capabilities?` | claim atomic; întoarce `run_id`, `lease_token`, `lease_expires_at` |
| `heartbeat` | `task_id`, `run_id`, `lease_token`, `extend_seconds?` | extinde lease-ul ownerului |
| `release_task` | `task_id`, `run_id`, `lease_token`, `reason` | eliberare voluntară → `ready` |
| `record_progress` | `task_id`, `run_id`, `lease_token`, `note` | progres; `claimed→running`, actualizează `last_progress_at` |
| `record_waiting_response` | `task_id`, `run_id`, `lease_token`, `awaiting_identity_id` (`pmorg.identity`, ADR-014), `timeout_at` | → `waiting_response` |
| `schedule_next_check` | `task_id`, `run_id`, `lease_token`, `next_check_at`, `reason` | → `scheduled`, eliberează lease-ul |
| `block_task` | `task_id`, `run_id`, `lease_token`, `reason` | → `blocked` |
| `complete_run` | `task_id`, `run_id`, `lease_token`, `outcome` (`done`\|`failed`\|`needs_review`), `summary`, `evidence_refs?` | închide run-ul; `done` cere `expected_outcome` acoperit sau `evidence_refs` ⇒ altfel `E_CRITERIA` |
| `record_evidence_reference` | `task_id`, `memory_ref`, `kind`, `note?` | leagă o referință de memorie/dovadă de task (eveniment) |
| `propose_task` | `initiative_id`, `name`, `pmorg_task_type`, `execution_mode`, `expected_outcome?`, `participant_ids?` | creează task `ready` legat de inițiativă |
| `record_confirmation` | `task_id`, `confirmed_by_partner_id`, `note?` | consemnează confirmarea (eveniment) |
| `request_approval` | `task_id`, `run_id`, `lease_token`, `subject`, `details` | → `waiting_approval` + eveniment |
| `request_outcome_verification` | `task_id`, `evidence_refs` | `verification_status → pending` |
| `reclaim_expired` | `now` | watchdog; întoarce run-urile recuperate |

Amânate explicit la `1.1` (definite, neimplementate în MVP-ul A.3):
`propose_plan_version`, `execute_authorized_command` (întoarce `E_AUTONOMY`
până există matricea de autonomie — fail-closed).

## 8. Outbox și inbox

- `pmorg.outbox.event` se scrie **în aceeași tranzacție** cu efectul: `seq`,
  `event_type`, `payload` (anvelopă + date), `created_at`. Consumatorul
  citește cu `after_seq` (at-least-once; consumatorul deduplichează pe
  `message_id`).
- Tipuri v1.0: `task.ready`, `task.claimed`, `task.progress`,
  `task.waiting_response`, `task.scheduled`, `task.blocked`,
  `task.released`, `task.run_completed`, `task.run_failed`,
  `task.lease_expired`, `task.approval_requested`,
  `task.verification_requested`, `initiative.state_changed`.
- `pmorg.command.inbox`: unicitate `(actor_id, idempotency_key)`; stochează
  răspunsul serializat; rejucarea întoarce răspunsul cu `status="replay"`.

## 9. Determinismul timpului

API-ul nu folosește ceasul serverului pentru decizii de scadență: `now` vine
în `list_due_work`, `claim_task` (validarea scadenței) și `reclaim_expired`.
Timestampurile de audit rămân pe ceasul serverului. Astfel timpul virtual al
runnerului MVP conduce longitudinalitatea fără patch-uri.

> **Reconciliere deschisă cu ADR-017 (Proposed):** în sandboxul de evaluare,
> timpul autoritativ se rezolvă server-side dintr-un `tick_id` emis de ceasul
> trusted; runtime-ul nu poate furniza un `now` autoritativ. Când ADR-017
> devine `Accepted`, parametrul `now` din comenzile mutante se înlocuiește cu
> `tick_id`, iar `now` client-side rămâne valid numai în afara harness-ului
> de evaluare (dev local). Schimbarea este incompatibilă ⇒ contract `2.0`.

## 10. Ce nu face acest contract

- nu expune `create/write/unlink` generic (ADR-006);
- nu schimbă stage-ul business al taskului;
- nu decide autonomie — poarta refuză, nu negociază (`E_AUTONOMY`);
- nu garantează exactly-once între sisteme: garantează idempotency la
  graniță și outbox at-least-once, conform 01-ARCHITECTURE §9.
