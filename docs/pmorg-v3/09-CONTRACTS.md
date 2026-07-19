# PMORG v3 — contracte v1

| Câmp | Valoare |
|---|---|
| Status | Accepted semantic baseline |
| Baseline | `RB-1/C1` |
| Contract package | `pmorg-contracts/1.0` |
| Data | 2026-07-18 |

Acest document îngheață semantica și câmpurile contractelor. La bootstrap,
fiecare tip devine JSON Schema cu `additionalProperties: false` pe writes și
primește digest content-addressed.

Acest pachet supersedează pentru v3 contractele v2, fără să le modifice
retroactiv. Maparea operațiilor, erorilor și idempotency este normativă în
[documentul de supersession](14-V2-CONTRACT-SUPERSESSION.md).

## 1. Convenții

- câmp fără `?` este obligatoriu; `T | null` este cheie obligatorie cu
  valoare posibil nulă;
- un câmp marcat `server-set` există în resursa normalizată/response, este
  interzis în write input și nu intră în `request_hash`;
- ID-urile PMORG noi sunt UUIDv7; excepția este `logical_entity_id`, care
  poate fi UUIDv5 derivat dintr-un namespace versionat pentru identitate
  logică deterministă; ID-urile Odoo sunt `int64`;
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

`operation` este exact `command_type` pentru o comandă Odoo, exact numele
operației din catalog pentru Semantic Core și `admit_message` ori
`execute_cognitive_step` pentru Turn API. `source_system` este
derivat server-side din principalul transport autentificat. Niciunul nu este
câmp client-controlled suplimentar: serverul le adaugă în cheia normalizată a
inboxului după validarea wire schema.

Serverul persistă `request_hash`. După finalizare, aceeași cheie și același
hash întorc același receipt durabil, byte-equivalent; transportul poate semnala
replay-ul într-un header/trace care nu modifică receipt-ul. Aceeași cheie cu
alt hash produce `IDEMPOTENCY_CONFLICT`. Lungimea maximă a cheii este 200
caractere.

O eroare de transport înainte ca inboxul să accepte comanda nu consumă cheia
și nu produce receipt. O respingere de domeniu cu `retryable=false` consumă
cheia și îngheață receipt-ul. O eroare tehnică `retryable=true` după acceptare
păstrează aceeași comandă în `retryable_pending`; workerul reia aceeași cheie
și același hash, cu attempt count durabil, fără un al doilea efect business.
După succes sau epuizarea politicii, receipt-ul final se îngheață. O comandă
logic diferită folosește cheie nouă și `retry_of`.

Pentru o comandă Odoo,
`request_hash` este hash-ul RFC 8785 al obiectului validat format din
`schema_version`, `command_type`, `payload_schema_version`, `context`, `actor`,
`authorization`, `preconditions`, `tick_id` și `payload`.
Sunt excluse numai metadatele de livrare/retry: `command_id`,
`declared_occurred_at`, `causation_id`, `retry_of` și `idempotency_key`.
`payload_hash` acoperă numai `payload`; `CommandReceipt.input_hash` este exact
`request_hash`. Coliziunea se verifică înaintea precondițiilor de business.

Pentru o acțiune care cere aprobare, `action_hash` este hash-ul RFC 8785 al
intenției business stabile:

```text
schema_version · command_type · payload_schema_version
context.{organization_id, odoo_instance_uuid, company_id, identity_id,
         profile_id, registry_version, registry_fingerprint,
         initiative_id, task_id}
actor.{actor_type, identity_id}
authorization.{policy_version, authority_grant_ref, autonomy_level}
preconditions.aggregate_ref.{organization_id, odoo_instance_uuid, company_id,
                             anchor_type, model, res_id}
preconditions.intent_state_hash
payload
```

Sunt excluse `approval_ref`, `runtime_id`, `run_id`, `conversation_id`,
`correlation_id`, `aggregate_ref.observed_write_date`,
`expected_state_version`, lease-ul, tick-ul și toate metadatele de
livrare/retry.
Approval-ul se leagă de `action_hash`; request-ul de execuție include apoi
`approval_ref`, contextul și lease-ul runului nou, iar `request_hash` le
acoperă. Serverul recalculează `action_hash` din execuție și îl compară cu
approval-ul. Astfel aprobarea nu depinde circular de propriul ID și supraviețuiește
închiderea runului care a cerut-o, fără a autoriza alt payload ori altă versiune
a stării business relevante acțiunii. Tranzițiile pur tehnice de
orchestrare pot schimba `expected_state_version` fără a invalida approval-ul;
orice câmp relevant acțiunii schimbă `intent_state_hash` și cere approval nou.

Pentru `execute_cognitive_step`, `request_hash` acoperă RFC 8785 toate
câmpurile validate din `CognitiveStepRequest`, exceptând `step_id`,
`causation_id` și `idempotency_key`. `admit_message` este excepția de frontieră:
înainte de privacy verdict dedup-ul folosește numai identitatea transportului
`(adapter_id, channel_account_id, external_message_id)`. La deny nu se persistă
request/content hash; la accept, operația durabilă începe cu evidence capture
și hash-ul ei canonic.

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

### 2.1 `LegacyProvenance`

Migrarea separă identitatea unică a rândului sursă de binding-urile sale
unu-la-mai-multe către obiectele v3:

```yaml
schema_version: const "pmorg.legacy-source-identity/v1"
legacy_identity_id: uuid  # server-set
organization_id: uuid
legacy_source_instance_id: "sha256:<hex>"
legacy_namespace: string
legacy_contract_version: string
legacy_type: evidence | claim | outcome | task | run | event | inbox_row
legacy_id: string
import_manifest_hash: "sha256:<hex>"
```

```yaml
schema_version: const "pmorg.legacy-provenance-binding/v1"
binding_id: uuid  # server-set
legacy_identity_id: uuid
target_system: odoo | semantic_core | migration_reference
target_type: string
target_id: string
relation_role: source_artifact | evidence | claim | assessment | validation | contradiction | supersession | commitment | outcome | task | run | event | reference_only
imported_at: rfc3339  # server-set
```

Identitatea sursă este unică pe
`(organization_id, legacy_source_instance_id, legacy_namespace, legacy_type,
legacy_id)`. Binding-ul este unic pe
`(legacy_identity_id, target_system, target_type, target_id, relation_role)`;
aceeași identitate legacy poate produce mai multe targeturi explicite — de
exemplu `SourceArtifact` + `Evidence` sau Claim + assessments + validation.
`legacy_source_instance_id` este digestul descriptorului canonic
din manifestul de import (repository, commit, sandbox, database UUID și
contract version), nu un nume introdus liber. Manifestul este verificat înainte
de write. Dacă source instance ori namespace-ul nu pot fi verificate, obiectul
rămâne `reference-only`: binding-ul indică un `migration_reference`, nu un
agregat Odoo/Semantic Core autoritativ. Relația este persistată separat, nu ca
un câmp permisiv adăugat obiectelor cu `additionalProperties: false`.
Pentru rândurile Odoo fără namespace legacy, adaptorul folosește exact
`odoo-db:<database_uuid>`; pentru memoria SB3 păstrează namespace-ul bazei.

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
capture. Recepția nu produce singură efect formal. Pentru inbound,
`content_ref` indică bufferul tranzitoriu al adaptorului de intrare până la privacy gate,
nu dovedește persistență PMORG. Dacă poarta refuză, bufferul se șterge și nu se
creează `EvidenceEnvelope`, transcript, index, prompt sau content receipt;
receipt-ul de refuz nu copiază `content_ref` ori `content_hash`.

Singurul artefact durabil al refuzului este:

```yaml
schema_version: const "pmorg.privacy-rejection-receipt/v1"
message_id: uuid
organization_id: uuid
adapter_id: string
policy_version: string
reason_code: privacy_policy_match | secret_pattern | unsafe_payload
received_at: rfc3339
correlation_id: uuid
```

Schema are `additionalProperties: false`. Nu include fragment, termen potrivit,
selector, content ref/hash, prompt, autor derivat din text sau metadata liberă.

După acceptare și capturarea evidence, Turn Admission emite singurul contract
inbound pe care îl pot primi orchestratorul/runnerul ori runtime-ul cognitiv:

```yaml
schema_version: const "pmorg.admitted-message/v1"
message_id: uuid
context: OrganizationContext
conversation_id: uuid
evidence_id: uuid
source_artifact_id: uuid
evidence_receipt_id: uuid
received_at: rfc3339
correlation_id: uuid
causation_id: uuid | null
```

`AdmittedMessage` nu conține și nu permite payload, transcript, `content_ref`
sau `content_hash`. Conținutul se citește ulterior numai prin Evidence ACL și
scopul explicit al pasului cognitiv. Un mesaj refuzat nu produce acest obiect.

## 5. `EvidenceEnvelope`

```yaml
schema_version: const "pmorg.evidence-envelope/v1"
evidence_id: uuid  # server-set
context: OrganizationContext
source_artifact:
  source_artifact_id: uuid  # server-set
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
recorded_at: rfc3339  # server-set
access_policy_ref: string
initiative_binding: int64 | null
task_binding: int64 | null
conversation_binding: uuid | null
causation_id: uuid | null
```

Evidence este imuabilă. Duplicatul întoarce aceeași evidence; două surse
independente rămân două evidence. `model_output` dovedește numai outputul
modelului. Payloadul mare rămâne în object store.

Receipt:

```yaml
operation_id: uuid
evidence_id: uuid
status: created
ledger_sequence: int64
recorded_at: rfc3339
input_hash: "sha256:<hex>"
```

Replay-ul întoarce exact acest receipt inițial; semnalul de transport nu îi
modifică `status`, `operation_id` sau `recorded_at`.

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
```

Proposal se creează numai în `proposed`, are minimum o evidence și minimum un
subject, exceptând `external_mention`. Predicate și anchor types există în
registry. Confidence nu acordă autoritate; validation, contradiction și
supersession sunt operații separate.

Un matching de ancoră ambiguu cu consecință nu produce `ClaimProposal` cu
ancoră incompletă. Evidence rămâne durabilă și creează obiectul separat
`pmorg.anchor.reconciliation`; după verdictul exclusiv asupra ancorei,
pipeline-ul reexecută automat extracția. UI/API-ul de reconciliere nu expune
câmpuri mutante pentru kind, owner, termen, predicate ori normalized value.

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
  intent_state_hash: "sha256:<hex>" | null
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
respingere terminală consumă cheia; o eroare tehnică retryable reia aceeași
comandă conform regulii din §1. După schimbarea versiunii, payloadului,
`action_hash`-ului sau approval-ului se emite command ID și cheie noi, cu
`retry_of` către comanda anterioară.

`intent_state_hash` este emis de preflight-ul server-side prin schema
versionată a comenzii peste numai câmpurile business care pot schimba
sensul/riscul acțiunii. Clientul îl poartă în wire inputul de approval/execuție,
deci intră în `request_hash`; serverul îl recalculează și îl verifică înainte
de write. Este obligatoriu pentru `approval_required`. Nu înlocuiește
optimistic concurrency: request-ul folosește în continuare versiunea și
lease-ul curente.

Enumul de autonomie din acest contract este unicul enum normativ. Policy
engine îl rezolvă înainte de emiterea `allowed_actions`. Pentru
`approval_required`, `approval_ref` este obligatoriu la execuție și trebuie
să corespundă `action_hash`-ului canonic definit în §1; `prohibited` nu poate
ajunge la execuție.

### 10.1 Catalog minim de comenzi

| `command_type` | Payload minim | Efect |
|---|---|---|
| `pmorg.task.claim` | `task_id, runtime_capabilities, requested_lease_seconds` | claim atomic și run |
| `pmorg.task.heartbeat` | `task_id, run_id, lease_token` | extinde lease-ul ownerului |
| `pmorg.task.release` | `task_id, run_id, reason_code` | eliberează/replanifică |
| `pmorg.task.record_progress` | `task_id, run_id, progress_code, summary_ref` | progres și audit |
| `pmorg.task.wait_response` | `task_id, conversation_id, expected_from, next_check_at` | wait condition |
| `pmorg.task.schedule` | `task_id, next_check_at, reason_code` | verificare viitoare |
| `pmorg.task.activate_due` | `task_id, trigger_type, trigger_ref` | system-only; `waiting_response\|waiting_approval\|scheduled → ready` numai la răspuns/approval corelat ori tick scadent |
| `pmorg.task.block` | `task_id, blocker, owner_identity_id, exit_condition` | blocker formal |
| `pmorg.task.mark_managed` | `task_id, monitoring_policy_ref` | `not_managed → ready`, cu versiune și audit |
| `pmorg.task.record_followup` | `task_id, intervention_id, conversation_id, outbound_message_id, message_receipt_ref, reason_code, policy_ref` | intervenție append-only; contor derivat, fără schimbarea implicită a stării taskului |
| `pmorg.task.record_escalation` | `task_id, escalation_id, recipient_identity_ids, trigger_ref, reason_code, policy_ref, evidence_refs` | escaladare append-only; nivel derivat server-side |
| `pmorg.run.reclaim_expired` | `task_id, run_id` | row lock; revocă lease-ul expirat și recuperează runul conform clasei efectului |
| `pmorg.provenance_gap.record_detection` | `detector_class, effect_ref, anchor_refs, window, materiality_policy_ref, signal_hash` | system-only; creează/rejoacă gap-ul pe dedup key |
| `pmorg.provenance_gap.resolve` | `gap_id, resolution_code, evidence_refs, memory_receipt_refs, policy_ref` | `open → explained\|dismissed` numai după verificarea receipts/politicii |
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

`record_followup` cere receipt-ul livrării: o propunere de mesaj nu este încă
intervenție. `record_escalation` cere pragul/politica evaluată, triggerul și
ținta decizională; serverul derivă nivelul, nu îl acceptă din payload.
Ambele cer lease valid și nu schimbă singure starea taskului; programarea
următoarei verificări rămâne comandă separată. `activate_due` este apelată de
controllerul determinist înaintea unui claim nou, verifică evenimentul sau
`next_check_at` cu timpul trusted și este idempotentă; modelul nu o poate
invoca. `reclaim_expired` este per-run,
folosește `expected_state_version`, row lock și numai timpul server-side sau
capabilitatea `tick_id`. El mută runul în `expired`, revocă lease-ul și pune
taskul în `ready` numai pentru efect sigur/retryable; un efect extern incert
intră în `review`. Cele patru comenzi au teste de portare pentru scenariile
longitudinale v2 S1/S9/watchdog; maparea este în
[14-V2-CONTRACT-SUPERSESSION](14-V2-CONTRACT-SUPERSESSION.md).

Comenzile `provenance_gap.*` nu sunt expuse modelului. Detection este permisă
numai identității de sistem a controllerului determinist; resolution verifică
live evidence/receipt-urile ori politica de dismiss și nu acceptă textul
modelului drept dovadă.

## 11. Command receipt și event

```yaml
schema_version: const "pmorg.odoo-command-receipt/v1"
command_id: uuid
context: OrganizationContext
status: applied | rejected | conflict | pending_approval | retryable_pending
idempotency_key: string
input_hash: "sha256:<hex>"
result_refs: [AnchorReference]
resulting_state_version: int64 | null
event_ids: [uuid]
processed_at: rfc3339
error: PMORGError | null
```

Valorile normative pentru `status` sunt `applied`, `rejected`, `conflict`,
`pending_approval` și `retryable_pending`; `replayed` nu este o stare de
receipt. Replay-ul întoarce receipt-ul durabil existent fără a-i modifica
statusul, timestampul sau ID-urile.

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

Fiecare apel folosește anvelopa comună:

```yaml
schema_version: const "pmorg.semantic-operation/v1"
operation_id: uuid
operation: enum din catalogul de mai jos
context: OrganizationContext
idempotency_key: string
body: obiect validat de schema operației
```

În cheia normalizată, `operation` este exact valoarea din anvelopă, iar
`source_system` este derivat din transportul autentificat. `request_hash` este
hash-ul RFC 8785 al `{schema_version, operation, semantic_context,
semantic_body}`. `semantic_context` conține toate câmpurile
`OrganizationContext` exceptând `run_id` și `correlation_id`; conversation și
scope-ul business rămân incluse. Sunt excluse mereu `operation_id`,
`idempotency_key`, câmpurile `server-set` și metadata de retry/transport.
Orice obiect body care repetă `context` trebuie să fie identic cu contextul
anvelopei curente; copia nested este apoi eliminată din `semantic_body`, astfel
încât contextul normalizat să fie hash-uit exact o dată.

Pentru `capture_evidence`, write projection exclude `evidence_id`,
`context`, `source_artifact.source_artifact_id`, `recorded_at` și
`causation_id`; serverul
rezolvă/creează ID-urile și întoarce valorile primei aplicări. Pentru
`propose_claim`, hash-ul exclude `proposal_id`,
`context`, `proposer.cognitive_execution_id` și `causation_id`, dar include
integral semantica, evidence, proposer identity și policy. Celelalte operații folosesc
toate câmpurile body declarate în tabel. Astfel un retry pe run/correlation nou
rejoacă aceeași operație logică, iar o schimbare de conținut, sursă, autoritate
sau sens produce conflict. Pentru fiecare operație, rădăcina normativă a lui
`semantic_body` este:

| Operație | Input principal | Output principal |
|---|---|---|
| `negotiate_registry` | `{descriptor, descriptor_hash}` | accepted version/types sau mismatch |
| `capture_evidence` | `{evidence: EvidenceEnvelope write projection}`; câmpurile excluse mai sus absente | evidence receipt |
| `propose_claim` | `{proposal: ClaimProposal}` | claim ID/status/version |
| `assess_claim` | `{claim_id, assessment_type, result, evidence_ids, assessor_authority_ref, policy_version}` | assessment receipt |
| `validate_claim` | `{claim_id, assessment_receipt_ids, validator_service_id, authority_ref, policy_version}` | validation decision |
| `record_contradiction` | `{left_claim_id, right_claim_id, kind, evidence_ids, valid_from, valid_to}` | contradiction ID/status |
| `supersede_claim` | `{old_claim_id, new_claim_id, scope, valid_from, valid_to, evidence_ids}` | supersession receipt |
| `record_commitment` | `{claim_id, commitment_anchor, evidence_ids, policy_version}` | memory/formalization binding |
| `record_outcome` | `{outcome_anchor, evidence_ids, verification_receipt_refs}` | outcome memory receipt |
| `recall` | `{query, anchors, temporal_scope, access_scope, status_filter}` | `MemoryView[]` |
| `get_timeline` | `{anchors, interval, as_of, access_scope}` | ordered semantic events |

MCP folosește protocol standard. Operațiile Turn Coordinator sunt apelate
determinist, nu lăsate ca tools opționale ale modelului.

`validate_claim` este invocat automat numai de policy engine/serviciul de
validare autorizat; `validator_service_id` trebuie să corespundă binding-ului
de transport. Identitățile umane și agentul cognitiv nu pot primi această
capabilitate. Un om poate furniza evidence într-o conversație, aproba un efect
business, verifica un outcome ori guverna vocabularul și ancora, dar nu poate
emite verdict, approval sau tranziție asupra interpretării claim-ului.

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
INVALID_TASK_TRANSITION · LEASE_REQUIRED · LEASE_HELD · LEASE_INVALID
LEASE_EXPIRED · NOT_DUE · POLICY_NOT_DUE · ODOO_UNAVAILABLE
LEDGER_UNAVAILABLE · RATE_LIMITED · RETRY_EXHAUSTED · INTERNAL_ERROR
```

`RETRY_EXHAUSTED` este terminal pentru command/key-ul curent și are
`retryable=false`; retry-ul unei intenții noi cere cheie nouă și `retry_of`.

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
