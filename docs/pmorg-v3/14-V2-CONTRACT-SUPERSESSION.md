# PMORG v3 — supersession-ul contractelor v2

| Câmp | Valoare |
|---|---|
| Status | Accepted — corrigendum `RB-1/C1` |
| Contract succesor | `pmorg-contracts/1.0` |
| Contracte superseded pentru v3 | orchestrator/Odoo v2 `1.0/1.1`; `pmorg-memory/1.0` |
| Referință | [PMORG-Platform#16](https://github.com/bmvv1995/PMORG-Platform/issues/16); [decizia ownerului 001a](../correspondence/001a-decizie-owner.md) |
| Data | 2026-07-18 |

## 1. Domeniul supersession-ului

[Contractele v2](../pmorg-v2/07-CONTRACTS.md) rămân înghețate și normative
pentru SB3 și pentru reproducerea rezultatelor v2. Ele sunt însă
**superseded pentru orice implementare v3** de
[`pmorg-contracts/1.0`](09-CONTRACTS.md), state machines v3 și cerințele
`RB-1/C1`.

Supersession-ul este incompatibil la wire level. Un client v2 nu apelează
direct un server v3 și un server v3 nu publică aliasuri v2 în API-ul său
canonic. Portarea testelor folosește un adaptor de compatibilitate izolat,
versionat și eliminabil; nu dual-write și nu două surse canonice.

Diferențele intenționate includ:

- context obligatoriu organization/instance/company/identity/registry;
- ID-uri PMORG noi UUIDv7, fără conversia serialelor v2 în identitate;
- evidence și claim separate, cu assessments și relații first-class;
- request hash obligatoriu pentru idempotency;
- erori de domeniu granulare;
- API intern de domeniu și MCP extern standard.

## 2. Maparea operațiilor memoriei: 8 → 11

| `pmorg-memory/1.0` v2 | `pmorg-contracts/1.0` v3 | Regula de portare |
|---|---|---|
| `memory_negotiate_registry` | `negotiate_registry` | descriptorul complet și `OrganizationContext` înlocuiesc `(profile, namespace, run)` implicit |
| `memory_capture_evidence` | `capture_evidence` | `EvidenceEnvelope` separă sursa, selectorul, autorul, timpii și scope-ul |
| `memory_propose_claim` | `propose_claim` | ancora v3 este `AnchorReference`; tipul/predicatul trebuie să existe în registry |
| `memory_validate_claim` | `assess_claim` + `validate_claim` | probele sunt persistate separat de verdictul policy engine-ului |
| `memory_supersede` | `supersede_claim` | scope-ul și intervalul de înlocuire devin obligatorii |
| `memory_record_outcome` | `record_outcome` | outcome evidence se leagă de formalizarea Odoo și de receipt |
| `memory_recall` | `recall` | filtrarea organization/company/ACL/registry/timp/status precede rezultatul |
| `memory_get_timeline` | `get_timeline` | valid time și recorded time sunt interogabile distinct |
| — | `record_contradiction` | relația incompatibilă este first-class, nu dedusă din recall |
| — | `record_commitment` | observarea semantică este legată explicit de commitment-ul formal Odoo |

Sunt unsprezece operații v3: cele opt operații efectiv implementate și
folosite de MVP-ul v2, cu validarea descompusă în assessment și verdict, plus
contradicția și commitment-ul first-class. V2 descria conceptual și
`memory_record_decision`/`memory_record_commitment`; primul devine
`propose_claim(claim_kind=decision)` + assessment + validation, iar al doilea este
promovat acum în operația explicită `record_commitment`.

### 2.1 Stări și identitate

| V2 | V3 | Regula de portare |
|---|---|---|
| claim `candidate` | `proposed` | fără promovare implicită la adevăr |
| claim `validated` | `validated` | numai dacă evidence și authority receipts pot fi reconstruite; altfel `proposed`/reference-only |
| claim `refuted` | `rejected`, `disputed` sau `reference-only` | `rejected` cere assessment evidence reconstructibilă; `disputed` cere atât validation receipt anterior, cât și contradiction receipt; statusul legacy singur nu permite alegerea și devine `reference-only` |
| claim `superseded` | `superseded` + relație `Supersession` | old/new, scope și interval trebuie reconstruite; lipsa lor blochează importul autoritativ |
| ID serial v2 | UUIDv7 v3 | se emite identitatea sursă [`LegacyProvenance`](09-CONTRACTS.md#21-legacyprovenance), unică pe `(organization_id, legacy_source_instance_id, legacy_namespace, legacy_type, legacy_id)`, apoi binding-uri 1:N către toate obiectele v3 rezultate; serialul nu este reinterpretat drept UUID |
| namespace/profil implicit | `OrganizationContext` explicit | maparea cere organization, Odoo instance, company și registry fingerprint verificabile |

Stările `under_review` nu se importă și nu se sintetizează: v3 nu are review
uman al interpretării claim-ului. Matching-ul de ancoră ambiguu intră în
obiectul separat `pmorg.anchor.reconciliation`.

Exemplu de conservare a autorității umane: formularea legacy „Paul validează”
se portează ca evidence/atestare sau autoritate business furnizată de Paul,
urmată de verdictul semantic automat al policy engine-ului. Paul poate aproba
efectul ori verifica outcome-ul conform ADR-005; nu primește capabilitatea
`validate_claim`. Separarea nu elimină autoritatea umană, ci o împiedică să
devină adnotare manuală asupra interpretării claim-ului.

## 3. Maparea erorilor memoriei

| Eroare v2 | Eroare v3 | Observație |
|---|---|---|
| `MEM_CONTRACT` | `UNSUPPORTED_SCHEMA_VERSION` | pachet/versiune incompatibilă; payloadul invalid rămâne `INVALID_ARGUMENT` |
| `MEM_SCHEMA` | `INVALID_ARGUMENT` | `field_violations` păstrează câmpurile invalide |
| `MEM_UNKNOWN` | `EVIDENCE_NOT_FOUND` sau `CLAIM_NOT_FOUND` | implementarea SB3 îl emite numai pentru evidence/claim absent; un live anchor failure v3 este validare nouă și nu se traduce din acest cod |
| `MEM_STATE` | `INVALID_CLAIM_TRANSITION` | pentru alte agregate se folosește eroarea lor de tranziție din schema dedicată |
| `MEM_REGISTRY_MISMATCH` | `REGISTRY_MISMATCH` | direct, fail-closed |
| `MEM_ANCHOR_TYPE_UNKNOWN` | `ANCHOR_TYPE_NOT_ALLOWED` | tip absent din registry-ul negociat |
| `MEM_NOT_AUTHORIZED` | `AUTHORITY_REQUIRED` | în SB3 codul indică lipsa autorității validatorului; `FORBIDDEN` v3 este o decizie ACL/policy nouă, nu traducere legacy |
| `MEM_SELF_VALIDATION` | `INDEPENDENT_VALIDATOR_REQUIRED` | validatorul este policy engine/serviciu autorizat, nu o coadă umană de interpretare |
| `MEM_HASH_MISMATCH` | `EVIDENCE_HASH_MISMATCH` | direct |
| `MEM_INTERNAL` | `INTERNAL_ERROR` | fără expunerea detaliilor interne |

Adaptorul de portare păstrează în trace codul v2 original și codul v3 rezultat.
El nu reduce erorile v3 la `MEM_UNKNOWN` pentru consumatorii v3.

## 4. Idempotency: migrare fără replay ambiguu

V2 are două mecanisme distincte care nu trebuie confundate:

- inboxul Odoo deduplica pe `(actor.id, idempotency_key)` și nu persista
  obligatoriu hash-ul cererii;
- memoria SB3 deduplica `capture_evidence` pe `(namespace, external_id)` și
  întorcea rândul existent chiar dacă source/author/content difereau.

V3 deduplica pe
`(organization_id, source_system, operation, idempotency_key)` și persistă
`request_hash`. `operation` este exact `command_type` pentru Odoo și exact
numele operației Semantic Core. Pentru memoria legacy, cheia v3 de
`capture_evidence` se derivă astfel:

```text
instance_descriptor = RFC8785({repository, commit_sha, sandbox_id,
                               database_uuid, legacy_contract_version})
legacy_source_instance_id = "sha256:" + hex(sha256(instance_descriptor))
source_system = "legacy-import/" + legacy_source_instance_id
idempotency_key = "v2e1:" + hex(sha256(RFC8785({
  legacy_source_instance_id, legacy_namespace, external_id
})))
```

Cheia are 69 caractere. Serverul acceptă importul numai prin identitatea de
serviciu legată unu-la-unu de digestul manifestului și derivă `source_system`
din acel binding; clientul nu îl trimite. Reimportul aceleiași instanțe printr-un
alt principal nelegat este refuzat, nu creează alt namespace de dedup.
`request_hash` este proiecția canonică integrală definită în contractul
Semantic Core, nu doar content hash-ul.

Testele de migrare obligatorii construiesc fixtures v2 și demonstrează:

1. aceeași cheie și același payload întorc același receipt, fără efect nou;
2. aceeași cheie și payload diferit întorc `IDEMPOTENCY_CONFLICT`;
3. un rând legacy fără payload original verificabil nu este importat ca inbox
   autoritativ; rămâne artefact `reference-only`;
4. nicio cheie nu este deduplicată între organizații sau operații distincte;
5. același `(legacy source instance, namespace, external_id)` și aceeași
   evidence canonică produc un singur receipt;
6. aceeași cheie memory legacy cu alt content, source ori author produce
   `IDEMPOTENCY_CONFLICT`, zero rând/effect nou și niciodată silent replay;
7. namespace-ul ori source instance diferit nu colizionează, chiar dacă
   `external_id` este identic.

MVP-ul nu importă date reale v1/v2. Acest test protejează semantica portării și
este precondiție pentru orice decizie ulterioară de import.

## 5. Comenzile longitudinale v2

Comenzile `mark_managed`, `record_followup`, `record_escalation` și
`reclaim_expired` nu sunt retrase. Succesorii lor
`pmorg.task.mark_managed`, `pmorg.task.record_followup`,
`pmorg.task.record_escalation` și `pmorg.run.reclaim_expired` apar în catalogul
[`OdooCommandEnvelope`](09-CONTRACTS.md#101-catalog-minim-de-comenzi), iar
scenariile v2 S1/S9/watchdog se portează pe acele comenzi. Succesul istoric
al SB3 nu este recalificat automat drept verdict v3. Primele și ultima sunt
în contractul v2 înghețat; follow-up/escalation au proveniență în raportul
V2-GD și implementarea v2 ca extensii declarate `1.1`.

### 5.1 Maparea efectelor task/run

Un run v2 activ nu se importă ca lease viu v3: tokenul, timpul trusted și
clasa efectului nu pot fi presupuse. Importerul păstrează runul legacy ca
provenance și materializează o stare v3 numai după următoarele reguli:

| Efect/stare v2 reconstructibilă | Run v3 | Task v3 | Condiție obligatorie |
|---|---|---|---|
| `mark_managed` / `not_managed → ready` | — | `ready` | eventul și versiunea taskului sunt reconstructibile |
| `complete_run(outcome=done)` | `succeeded` | `completed` | outcome/evidence și receipt-ul efectului sunt verificabile; altfel `review` |
| `complete_run(outcome=failed)` | `failed` | `failed` | reason/error classification sunt păstrate |
| `complete_run(outcome=needs_review)` | `succeeded` | `review` | rezultatul propus rămâne evidence, nu verdict automat |
| `release_task` voluntar | `cancelled` cu reason legacy | `ready` | nu există efect extern început ori incert |
| `record_waiting_response` / wait activ | `succeeded` | `waiting_response` | recipientul, conversation, delivery receipt și timeout sunt reconstructibile; altfel `review` |
| `request_approval` / approval activ | `succeeded` | `waiting_approval` | action hash, policy, approver scope și expiry sunt reconstructibile; altfel `review`/`reference-only` |
| `schedule_next_check` | `succeeded` | `scheduled` | `next_check_at`, ceasul/sursa și motivul sunt reconstructibile |
| `block_task` | `succeeded` | `blocked` | blockerul, ownerul și condiția de ieșire sunt reconstructibile; altfel `review`/`reference-only` |
| `record_followup` | — | starea curentă nu se schimbă | se importă un singur `pmorg.intervention` append-only numai cu conversation, outbound message, delivery receipt, policy/reason și timp verificabile; `followup_count` se recalculează din evenimente acceptate |
| `record_escalation` | — | starea curentă nu se schimbă | se importă un singur escalation event numai cu destinatari, trigger, policy/reason, evidence și timp verificabile; nivelul se derivă server-side din evenimentele acceptate |
| lease expirat / `reclaim_expired` | `expired` | `ready` sau `review` | `ready` numai pentru `read_only` ori efect idempotent cu receipt complet; `review` pentru efect extern incert |
| `claimed`/`running` live la cutover | niciun run viu importat | `ready` sau `review` | aceeași regulă de effect class; lease-ul legacy este revocat |

`effect_class` este derivată numai din command/delivery receipts și evente:
`read_only`, `idempotent_receipted` sau `external_uncertain`. Lipsa dovezii
produce `external_uncertain`, deci `review`; textul de summary nu poate coborî
riscul. `followup_count`, `escalation_level` și `state_version` legacy nu se
importă drept adevăr independent și nu se folosesc pentru a sintetiza evenimente
lipsă. Importerul ordonează evenimentele reconstructibile după
`(occurred_at, legacy_event_id)`, le rejucă idempotent și atribuie o versiune
agregată v3 nouă, monotonă; valorile legacy rămân numai în provenance. După
import, răspunsul ori tick-ul scadent folosește
`pmorg.task.activate_due`, apoi un run v3 nou.

Testul adaptorului pentru S1/S9 este obligatoriu și este urmărit prin
[`F-MIG-LONG-001`](12-ACCEPTANCE-TRACEABILITY.md#8-g3-f--longitudinalitate-și-recovery):

1. nota legacy plus conversation, outbound message și delivery receipt
   corelate produce exact un `pmorg.intervention` și contor derivat `1`;
2. nota legacy fără delivery receipt rămâne `reference-only`, produce zero
   intervenții v3 și nu incrementează contorul;
3. replay-ul fixture-ului produce același event/receipt, fără al doilea
   follow-up ori altă versiune agregată.

## 6. Pointer normativ pentru refuzul porții de intimitate

Contractul explicit este în
[`MessageEnvelope` și `PrivacyRejectionReceipt`](09-CONTRACTS.md#4-messageenvelope),
iar proba obligatorie este
[`C-PRIVACY-001`](12-ACCEPTANCE-TRACEABILITY.md#5-g3-c--semantic-core).
La refuz, singurul artefact durabil este receipt-ul metadata-only; nu se
persistă conținut, fragment, `content_ref`, `content_hash`, transcript,
evidence, chunk, prompt ori checkpoint orchestrator/runner și nu se emite
`AdmittedMessage`.
