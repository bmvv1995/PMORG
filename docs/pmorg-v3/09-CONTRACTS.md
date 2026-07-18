# PMORG v3 — contracte v1

| Câmp | Valoare |
|---|---|
| Status | Accepted semantic baseline |
| Baseline | `RB-1` |
| Contract package | `pmorg-contracts/1.0` |
| Data | 2026-07-18 |

Acest document îngheață semantica și câmpurile contractelor. La bootstrap,
fiecare tip devine JSON Schema cu `additionalProperties: false` pe writes și
primește digest content-addressed.

## 1. Convenții

- câmp fără `?` este obligatoriu; `T | null` este cheie obligatorie cu
  valoare posibil nulă;
- ID-urile PMORG noi sunt UUIDv7; ID-urile Odoo sunt `int64`;
- timpii sunt RFC3339 UTC;
- hash-ul este `sha256:<hex>` peste bytes exacți sau JSON canonicalizat
  RFC 8785;
- `schema_version` are forma `pmorg.<contract>/v1`;
- versiunea majoră necunoscută și câmpurile write necunoscute sunt refuzate;
- timpul clientului este declarat, nu autoritativ;
- niciun tenant, ID, rol, registry sau drept nu este dedus din text.

Scope-ul idempotency este:

```text
(organization_id, source_system, operation, idempotency_key)
```

Serverul persistă `request_hash`. Aceeași cheie și același hash întorc
receipt-ul inițial; aceeași cheie cu alt hash produce
`IDEMPOTENCY_CONFLICT`. Lungimea maximă a cheii este 200 caractere.

## 2. `OrganizationContext`

```yaml
schema_version: const "pmorg.organization-context/v1"
organization_id: uuid
odoo_instance_uuid: uuid
company_id: int64
identity_id: uuid
profile_id: string
registry_version: semver
registry_fingerprint: "sha256:<hex>"
initiative_id: int64 | null
task_id: int64 | null
run_id: uuid
conversation_id: uuid | null
correlation_id: uuid
```

Toate cheile sunt obligatorii. Scope-ul corespunde binding-ului autentificat;
identitatea este activă; inițiativa și taskul aparțin aceluiași tenant;
contextul nu se schimbă în interiorul aceluiași run. Un mesaj neidentificat
rămâne în gateway reconciliation și nu primește context valid.

## 3. `AnchorReference`

```yaml
schema_version: const "pmorg.anchor-reference/v1"
logical_entity_id: uuid
organization_id: uuid
odoo_instance_uuid: uuid
company_id: int64
anchor_type: string
model: string
res_id: int64
registry_version: semver
schema_fingerprint: "sha256:<hex>"
observed_write_date: rfc3339
relation_role: string
```

Rezoluția verifică live organizația, compania, modelul, recordul, ACL-ul,
tipul din registry și `observed_write_date`. `model + res_id` nu este ancoră
validă.

## 4. `MessageEnvelope`

```yaml
schema_version: const "pmorg.message-envelope/v1"
message_id: uuid
direction: inbound | outbound
context: OrganizationContext
external_message_id: string | null
adapter_id: string
channel_id: string
channel_account_id: string
verified_principal:
  principal_type: user | bot | system
  principal_id: string
  verification_method: string
identity_binding:
  identity_id: uuid
  binding_version: string
conversation_id: uuid
reply_to_message_id: uuid | null
causation_id: uuid | null
content:
  content_ref: uri
  content_hash: "sha256:<hex>"
  media_type: string
  language: string | null
source_declared_at: rfc3339 | null
received_at: rfc3339 | null
sent_at: rfc3339 | null
idempotency_key: string
metadata?: adapter-specific allow-listed object
```

Inbound cere external ID și `received_at`; inbound se deduplichează pe
`(adapter_id, channel_account_id, external_message_id)`. Retry-ul outbound nu
creează al doilea mesaj logic. Hash-ul se verifică înainte de evidence
capture. Recepția nu produce singură efect formal.

## 5. `EvidenceEnvelope`

```yaml
schema_version: const "pmorg.evidence-envelope/v1"
evidence_id: uuid
context: OrganizationContext
source_artifact:
  source_artifact_id: uuid
  source_type: message | document | file | observation | system_event | model_output
  origin_system: string
  origin_ref: string
  content_ref: uri
  content_hash: "sha256:<hex>"
  media_type: string
selector:
  type: whole | byte_range | text_range | json_pointer | page_region
  value: object
author_identity_id: uuid
author_anchor?: AnchorReference
declared_occurred_at: rfc3339 | null
captured_at: rfc3339
recorded_at: rfc3339
access_policy_ref: string
initiative_binding: int64 | null
task_binding: int64 | null
conversation_binding: uuid | null
causation_id: uuid | null
idempotency_key: string
```

Evidence este imuabilă. Duplicatul întoarce aceeași evidence; două surse
independente rămân două evidence. `model_output` dovedește numai outputul
modelului. Payloadul mare rămâne în object store.

Receipt:

```yaml
operation_id: uuid
evidence_id: uuid
status: created | replayed
ledger_sequence: int64
recorded_at: rfc3339
input_hash: "sha256:<hex>"
```

## 6. `ClaimProposal`

```yaml
schema_version: const "pmorg.claim-proposal/v1"
proposal_id: uuid
context: OrganizationContext
claim_kind: fact | decision | commitment | preference | observation | hypothesis | external_mention
subject_refs: [AnchorReference]
predicate: string
normalized_value:
  value_type: string | number | boolean | date | datetime | duration | money | anchor | json
  value: any
  unit?: string
  currency?: string
  schema_ref?: uri
evidence_refs: [uuid]
proposer:
  identity_id: uuid
  actor_type: user | agent | system
  cognitive_execution_id: uuid | null
valid_from: rfc3339 | null
valid_to: rfc3339 | null
confidence_metadata:
  score: number[0..1] | null
  method: string
  explanation: string | null
policy_version: string
causation_id: uuid | null
idempotency_key: string
```

Proposal se creează numai în `proposed`, are minimum o evidence și minimum un
subject, exceptând `external_mention`. Predicate și anchor types există în
registry. Confidence nu acordă autoritate; validation, contradiction și
supersession sunt operații separate.

## 7. `Commitment`

Commitment-ul formal este legat de claim-ul de tip `commitment`, dar are
lifecycle operațional separat:

```yaml
schema_version: const "pmorg.commitment/v1"
commitment_id: uuid
context: OrganizationContext
claim_id: uuid
committer_identity_id: uuid
beneficiary_identity_id: uuid | null
task_binding: int64 | null
expected_action:
  action_type: string
  description: string
  anchor_refs: [AnchorReference]
due_at: rfc3339
status: proposed | awaiting_confirmation | confirmed | fulfilled | breached | fulfilled_late | cancelled | superseded
confirmation_evidence_refs: [uuid]
confirmed_at: rfc3339 | null
fulfillment_evidence_refs: [uuid]
fulfilled_at: rfc3339 | null
breach_detected_at: rfc3339 | null
supersedes_commitment_id: uuid | null
policy_version: string
state_version: int64
idempotency_key: string
```

`confirmed` cere evidence a confirmării sau excepție autorizată. `due_at`
este evaluat server-side; primul tick după termen mută obiectul neîndeplinit
în `breached`. Îndeplinirea ulterioară produce `fulfilled_late`. Schimbarea
responsabilului, termenului sau acțiunii creează commitment nou și
supersession; nu modifică în loc obiectul confirmat.

## 8. `CognitiveStepRequest`

```yaml
schema_version: const "pmorg.cognitive-step-request/v1"
step_id: uuid
context: OrganizationContext
objective:
  objective_type: string
  instruction: string
  success_criterion_refs: [int64]
  constraints: [string]
observed_state:
  initiative_state_version: int64
  task_state_version: int64 | null
  state_hash: "sha256:<hex>"
  observed_at: rfc3339
allowed_actions:
  - action_id: string
    action_schema_version: string
    autonomy_level: read | recommend | execute_delegated | approval_required | prohibited
    exposed_to_model: boolean
    max_calls: integer
evidence_refs: [uuid]
policy_refs: [string]
current_wait_condition: object | null
tick_id: string | null
causation_id: uuid | null
idempotency_key: string
execution_limits:
  max_output_items: integer
  deadline_ms: integer
```

## 9. `CognitiveStepResult`

```yaml
schema_version: const "pmorg.cognitive-step-result/v1"
step_id: uuid
context: OrganizationContext
status: completed | needs_clarification | waiting | blocked | no_action
observed_state:
  initiative_state_version: int64
  task_state_version: int64 | null
  state_hash: "sha256:<hex>"
summary: string
evidence_receipts: [uuid]
claim_proposals: [ClaimProposal]
business_command_proposals:
  - proposal_id: uuid
    action_id: string
    payload_schema_version: string
    payload: object
    evidence_refs: [uuid]
messages_to_send:
  - message_proposal_id: uuid
    conversation_id: uuid
    recipient_anchor: AnchorReference
    content_ref: uri
    content_hash: "sha256:<hex>"
    channel_policy_ref: string
    reply_to_message_id: uuid | null
wait_condition: object | null
recommended_next_check:
  policy_delay: iso8601-duration | null
  reason: string | null
explanation:
  evidence_used: [uuid]
  assumptions: [string]
  unresolved_questions: [string]
  rationale: string
model_execution_ref: uuid | null
result_hash: "sha256:<hex>"
completed_at: rfc3339
```

Action IDs sunt subset al celor permise. `prohibited` implică
`exposed_to_model=false`; `approval_required` produce numai propunere până la
approval; `execute_delegated` permite efect numai prin preflight și comandă
controlată. Rezultatul conține propuneri, nu
efecte pretins executate. `waiting` cere wait condition și next check;
`blocked` cere motiv și zero comandă executabilă. O versiune Odoo schimbată
produce `VERSION_CONFLICT`. Retry-ul întoarce rezultatul persistat.

## 10. `OdooCommandEnvelope`

```yaml
schema_version: const "pmorg.odoo-command/v1"
command_id: uuid
command_type: string
payload_schema_version: string
context: OrganizationContext
actor:
  actor_type: user | agent | system
  identity_id: uuid
  runtime_id: string
authorization:
  policy_version: string
  authority_grant_ref: string | null
  approval_ref: string | null
  autonomy_level: read | recommend | execute_delegated | approval_required | prohibited
preconditions:
  aggregate_ref: AnchorReference
  expected_state_version: int64 | null
  lease: {run_id: uuid, lease_token: string} | null
tick_id: string | null
declared_occurred_at: rfc3339 | null
causation_id: uuid | null
retry_of: uuid | null
idempotency_key: string
payload: object
payload_hash: "sha256:<hex>"
```

Minimum una dintre `expected_state_version` și `lease` este nenulă. Pentru
create se verifică versiunea agregatului părinte și cheia idempotentă. O
comandă refuzată consumă cheia sa; după schimbarea versiunii, payloadului sau
approval-ului se emite command ID și cheie noi, cu `retry_of` către comanda
anterioară.

Enumul de autonomie din acest contract este unicul enum normativ. Policy
engine îl rezolvă înainte de emiterea `allowed_actions`. Pentru
`approval_required`, `approval_ref` este obligatoriu la execuție și trebuie
să corespundă command hash-ului; `prohibited` nu poate ajunge la execuție.

### 10.1 Catalog minim de comenzi

| `command_type` | Payload minim | Efect |
|---|---|---|
| `pmorg.task.claim` | `task_id, runtime_capabilities, requested_lease_seconds` | claim atomic și run |
| `pmorg.task.heartbeat` | `task_id, run_id, lease_token` | extinde lease-ul ownerului |
| `pmorg.task.release` | `task_id, run_id, reason_code` | eliberează/replanifică |
| `pmorg.task.record_progress` | `task_id, run_id, progress_code, summary_ref` | progres și audit |
| `pmorg.task.wait_response` | `task_id, conversation_id, expected_from, next_check_at` | wait condition |
| `pmorg.task.schedule` | `task_id, next_check_at, reason_code` | verificare viitoare |
| `pmorg.task.block` | `task_id, blocker, owner_identity_id, exit_condition` | blocker formal |
| `pmorg.task.propose` | `initiative_id, task_type, title, expected_outcome, assignee, due_at, anchors` | task controlat |
| `pmorg.plan.propose_version` | `initiative_id, base_version, tasks, rationale, evidence_refs` | plan version candidat |
| `pmorg.commitment.record_confirmation` | `commitment_id, confirmer, confirmation_evidence` | confirmare formală |
| `pmorg.approval.request` | `action_hash, action_type, approver_policy, expires_at` | approval pending |
| `pmorg.evidence.record_reference` | `target_ref, evidence_id, relation_role` | leagă ledgerul de Odoo |
| `pmorg.outcome.request_verification` | `outcome_id, criterion_refs, evidence_refs` | pornește verificarea |
| `pmorg.action.execute_authorized` | `action_type, action_payload, approval_ref` | efect din allow-list |
| `pmorg.run.complete` | `task_id, run_id, result_code, receipt_refs` | încheie runul |

Fiecare payload devine schemă proprie înaintea endpointului. Catalogul nu
permite un `model`, `method`, `values` generic.

## 11. Command receipt și event

```yaml
schema_version: const "pmorg.odoo-command-receipt/v1"
command_id: uuid
context: OrganizationContext
status: applied | replayed | rejected | conflict | pending_approval
idempotency_key: string
input_hash: "sha256:<hex>"
result_refs: [AnchorReference]
resulting_state_version: int64 | null
event_ids: [uuid]
processed_at: rfc3339
error: PMORGError | null
```

```yaml
schema_version: const "pmorg.odoo-event/v1"
event_id: uuid
event_type: string
payload_schema_version: string
context: OrganizationContext
aggregate_ref: AnchorReference
aggregate_version: int64
outbox_id: int64
source_command_id: uuid | null
correlation_id: uuid
causation_id: uuid | null
occurred_at: rfc3339
recorded_at: rfc3339
tick_id: string | null
payload: object
payload_hash: "sha256:<hex>"
```

Efectul business, receipt-ul și outbox event se scriu în aceeași tranzacție.
`event_id` rămâne identic la redelivery; ordinea este dată de
`aggregate_version`, nu de ordine globală.

## 12. Semantic Core API și MCP

| Operație | Input principal | Output principal |
|---|---|---|
| `negotiate_registry` | context + descriptor/hash | accepted version/types sau mismatch |
| `capture_evidence` | `EvidenceEnvelope` | evidence receipt |
| `propose_claim` | `ClaimProposal` | claim ID/status/version |
| `assess_claim` | claim + assessment/evidence | assessment receipt |
| `validate_claim` | claim + validator/authority/policy | validation decision |
| `record_contradiction` | claim IDs + kind/evidence | contradiction ID/status |
| `supersede_claim` | old/new claims + scope/interval | supersession receipt |
| `record_commitment` | claim validat + Odoo binding | memory/formalization binding |
| `record_outcome` | evidence + Odoo binding | outcome memory receipt |
| `recall` | context + query + temporal/access scope | `MemoryView[]` |
| `get_timeline` | context + anchors + interval/as-of | ordered semantic events |

MCP folosește protocol standard. Operațiile Turn Coordinator sunt apelate
determinist, nu lăsate ca tools opționale ale modelului.

## 13. `PMORGError`

```yaml
schema_version: const "pmorg.error/v1"
error_id: uuid
code: enum
message: string
retryable: boolean
retry_after_ms: integer | null
correlation_id: uuid
run_id: uuid | null
operation: string
field_violations: [{field: json-pointer, reason: string}]
details: object | null
```

Coduri minime:

```text
INVALID_ARGUMENT · UNSUPPORTED_SCHEMA_VERSION · INVALID_CONTEXT
UNAUTHENTICATED · IDENTITY_UNBOUND · FORBIDDEN · CROSS_TENANT_SCOPE
REGISTRY_MISMATCH · ANCHOR_TYPE_NOT_ALLOWED · ANCHOR_NOT_FOUND
ANCHOR_STALE · ANCHOR_ACL_DENIED · EVIDENCE_NOT_FOUND
EVIDENCE_HASH_MISMATCH · CLAIM_NOT_FOUND · INVALID_CLAIM_TRANSITION
AUTHORITY_REQUIRED · INDEPENDENT_VALIDATOR_REQUIRED · TEMPORAL_INVALID
CONTRADICTION_UNRESOLVED · IDEMPOTENCY_CONFLICT · VERSION_CONFLICT
LEASE_REQUIRED · LEASE_INVALID · LEASE_EXPIRED · ODOO_UNAVAILABLE
LEDGER_UNAVAILABLE · RATE_LIMITED · INTERNAL_ERROR
```

Eșecurile de domeniu MCP folosesc `isError=true` și eroarea în
`structuredContent`. Răspunsul nu expune stack trace, SQL, secrete sau
existența obiectelor altui tenant. Succesul și eroarea propagă correlation ID.

## 14. Compatibilitate și freeze

- câmpul opțional nou de răspuns poate fi minor version;
- câmp obligatoriu nou, semantică schimbată ori enum eliminat cere major;
- producerul și consumerul negociază versiunea înaintea runului;
- manifestul fixează digestul pachetului de scheme;
- contract tests folosesc cel puțin un client independent de implementarea
  serverului.
