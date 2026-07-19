# PMORG v3 — contracte v1

| Câmp | Valoare |
|---|---|
| Status | Accepted semantic baseline |
| Baseline | `RB-1/C2` |
| Contract package | `pmorg-contracts/1.0` |
| Data | 2026-07-19 |

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

### 1.1 Evidence offline, semnături și setul exact de artefacte

Niciun hash dintr-un verdict de calificare/admission nu este o dovadă de unul
singur. Fiecare digest referit trebuie să rezolve exact un artefact ale cărui
bytes sunt livrate în același release/evidence bundle:

```yaml
EvidenceArtifactRef:
  logical_name: string
  media_type: string
  digest: "sha256:<hex>"
  size_bytes: int64
  relative_path: string

EvidenceBundleIndex:
  schema_version: const "pmorg.evidence-bundle-index/v1"
  bundle_kind: string
  subject_binding_hash: "sha256:<hex>" | null
  entries: nonempty array[EvidenceArtifactRef]
  entry_count: int64
```

`entries` este sortat canonic după `logical_name`, iar numele, digesturile și
`relative_path` sunt unice. `entry_count` este exact lungimea array-ului.
Digestul bundle-ului este hash-ul payloadului RFC 8785 al indexului; indexul
nu își conține propriul digest. `subject_binding_hash`, dacă există, leagă un
input preexistent independent (de exemplu artifact set ori target descriptor),
niciodată payloadul/envelope-ul consumator sau indexul însuși. Missing bytes,
bytes cu alt digest, path escape, intrări duplicate, circularitate ori
artefacte referite dar neindexate produc `INVALID`.

Toate atestările și admission records sunt payloaduri JSON fără câmp de
semnătură, împachetate într-un envelope DSSE separat:

```yaml
DsseEnvelope:
  payloadType: string
  payload: base64(rfc8785_json_bytes)
  signatures: nonempty array[{keyid: string, sig: base64}]
```

Semnătura acoperă DSSE PAE pentru `payloadType + payload`. Digestul envelope-ului
este calculat extern și poate fi referit de alt payload; nici payloadul, nici
envelope-ul nu își conțin propriul hash. Trust root-ul, cheia/cert-chain-ul,
policy digest-ul, verifier receipt-ul și revocation evidence sunt
`EvidenceArtifactRef` obligatorii în bundle-ul payloadului. Verificarea offline
refuză un envelope dacă oricare dintre acești bytes lipsește, nu corespunde
digestului, este neacceptat ori revocat. `verification_policy_hash` trebuie să
coincidă cu pinul din baseline manifest; trust material livrat numai de
artefactul verificat nu se poate auto-autoriza. Fiecare payload semnat include
`verifier_identity`, `verification_policy_hash`,
`verification_material_bundle` și `issued_at`; acestea sunt în payloadul
semnat, nu metadata neacoperită a envelope-ului.
Verifier receipt-ul leagă exact inputurile deciziei (build, descriptor,
measurement și authorization aplicabilă), dar nu hash-ul payloadului ori al
envelope-ului final. Graful tuturor evidence refs trebuie să fie aciclic; o referință
înapoi la payload, envelope ori propriul index este `INVALID`.

Setul deployabil este inventarul canonic al tuturor imaginilor, workerelor și
pachetelor livrate:

```yaml
ReleaseBuildDefinitionPayload:
  schema_version: const "pmorg.release-build-definition/v1"
  baseline_manifest_hash: "sha256:<hex>"
  pmorg_spec_commit: full_git_sha
  pmorg_platform_commit: full_git_sha
  onyx_commit: full_git_sha
  onyx_surface: enum[ce, ee]
  allowed_usage_modes: nonempty array[enum[development_test, production]]
  build_recipe: EvidenceArtifactRef
  build_input_set: EvidenceArtifactRef
  expected_artifact_catalog_hash: "sha256:<hex>"
  qualification_policy_map_hash: "sha256:<hex>"
  runtime_scope_policy_map: EvidenceArtifactRef
  approval_authority: EvidenceArtifactRef
  verifier_identity: string
  verification_policy_hash: "sha256:<hex>"
  verification_material_bundle: EvidenceArtifactRef
  issued_at: rfc3339_utc

ExpectedArtifactCatalogItem:
  artifact_id: string
  component: string
  artifact_kind: enum[oci_image, worker, package, migration, static_bundle]
  media_type: string
  platform: string

ExpectedArtifactCatalog:
  schema_version: const "pmorg.expected-artifact-catalog/v1"
  build_recipe_hash: "sha256:<hex>"
  items: nonempty array[ExpectedArtifactCatalogItem]
  expected_artifact_count: int64

RuntimeScopePolicyMap:
  schema_version: const "pmorg.runtime-scope-policy-map/v1"
  baseline_manifest_hash: "sha256:<hex>"
  onyx_surface: enum[ce, ee]
  entries: nonempty sorted array[
    {
      scope_class: enum[deployment_runtime, registry_publish, artifact_export],
      scope_policy_hash: "sha256:<hex>",
      expected_artifact_id_set_hash: "sha256:<hex>",
      expected_release_metadata_role_set_hash: "sha256:<hex>" | null,
      target_destination_policy_schema_hash: "sha256:<hex>"
    }
  ]

ArtifactDescriptor:
  artifact_id: string
  component: string
  artifact_kind: enum[oci_image, worker, package, migration, static_bundle]
  media_type: string
  platform: string
  digest: "sha256:<hex>"
  size_bytes: int64
```

Catalogul și descriptorii sunt sortați strict după cheia totală
`artifact_id + platform + media_type`; cheia și `artifact_id` sunt unice, iar
count-ul catalogului este lungimea array-ului. Catalogul așteptat provine din
build recipe-ul fixat, nu din outputul observat. Proiecția fiecărui descriptor
fără `digest` și `size_bytes` trebuie să fie exact elementul omolog din catalog.
`artifact_set_hash` este SHA-256 peste array-ul RFC 8785 al descriptorilor, iar
`image_lock_hash` leagă fiecare `artifact_id` de repository/digest imutabil,
fără taguri mutabile.

`ReleaseBuildDefinitionPayload` are DSSE envelope semnat de autoritatea de
release acceptată printr-un trust policy pin extern buildului. El ancorează
rețeta, inputurile, expected catalogul și policy map-ul înainte de execuția
buildului; bytes-ii sunt în qualification bundle. Buildul nu poate furniza o
definiție alternativă care să se auto-autorizeze.

`RuntimeScopePolicyMap` are exact câte un entry unic pentru
`deployment_runtime`, `registry_publish` și `artifact_export`, fără entry-uri
necunoscute ori duplicate. `baseline_manifest_hash` și `onyx_surface` sunt
exact egale cu release definition și BQM. Pentru `deployment_runtime`,
`expected_release_metadata_role_set_hash` este null; pentru cele două clase de
distribuție este non-null. Set hashes sunt SHA-256 peste array-uri RFC 8785
sortate și fără duplicate; setul de artefacte pentru `deployment_runtime` este
exact întregul catalog așteptat, iar cele de distribuție sunt subseturile
fixate de release authority înainte de build. Policy schema refs rezolvă la
bytes prin verification material-ul extern fixat. Watchdog-ul și revalidarea
unui transfer nu aleg un scope nou: refolosesc entry-ul fixat de operația
părinte din admission.

`BuildQualificationManifest` este un payload detașat; nu este inclus în
artefactele ale căror digesturi le conține:

```yaml
schema_version: const "pmorg.build-qualification-manifest/v1"
baseline_manifest_hash: "sha256:<hex>"
release_build_definition_envelope_hash: "sha256:<hex>"
build_recipe_hash: "sha256:<hex>"
build_input_set_hash: "sha256:<hex>"
runtime_scope_policy_map_hash: "sha256:<hex>"
expected_artifact_catalog_hash: "sha256:<hex>"
artifact_descriptors: nonempty array[ArtifactDescriptor]
artifact_count: int64
expected_artifact_count: int64
missing_artifact_count: int64
unexpected_artifact_count: int64
duplicate_artifact_key_count: int64
artifact_set_hash: "sha256:<hex>"
image_lock_hash: "sha256:<hex>"
pmorg_platform_commit: full_git_sha
pmorg_spec_commit: full_git_sha
onyx_release_tag: string
onyx_commit: full_git_sha
onyx_surface: enum[ce, ee]
usage_mode: enum[development_test, production]
qualification_policy_map_hash: "sha256:<hex>"
sbom_hash: "sha256:<hex>"
license_report_hash: "sha256:<hex>"
patch_ledger_report_hash: "sha256:<hex>"
provenance_report_hash: "sha256:<hex>"
provenance_evidence_bundle_index_hash: "sha256:<hex>"
surface_mode_report_hash: "sha256:<hex>"
capability_catalog_hash: "sha256:<hex>"
capability_disposition_report_hash: "sha256:<hex>"
capability_evidence_bundle_index_hash: "sha256:<hex>"
vulnerability_report_hash: "sha256:<hex>"
upstream_test_report_hash: "sha256:<hex>"
ce_boundary_report_hash: "sha256:<hex>" | null
ee_inventory_report_hash: "sha256:<hex>" | null
qualification_bundle_index_hash: "sha256:<hex>"
```

PASS cere `artifact_count=expected_artifact_count`, egal cu lungimea array-ului,
și zero missing/unexpected/duplicate. `qualification_bundle_index_hash` leagă
un `EvidenceBundleIndex` care conține bytes pentru toate rapoartele și
inventarele de mai sus; manifestul însuși nu intră în bundle. Pentru
`bundle_kind=build_qualification`, `logical_name` are setul exact:
`release-build-definition-dsse`, `build-recipe`, `build-input-set`,
`runtime-scope-policy-map`,
`expected-artifact-catalog`, `image-lock`, `qualification-policy-map`,
`sbom-index`, `license-report`,
`patch-ledger-report`, `provenance-report`, `surface-mode-report`,
`provenance-evidence-bundle-index`, `capability-catalog`,
`capability-disposition-report`, `capability-evidence-bundle-index`,
`vulnerability-report`,
`upstream-test-report` și exact unul dintre
`ce-boundary-report|ee-inventory-report`. Missing/duplicate/unknown role ori
rol condițional greșit invalidează bundle-ul. Pentru `ce`, CE boundary este
obligatoriu și EE inventory este null; pentru `ee`, regula este inversă.

Maparea dintre BQM și index este unu-la-unu și normativă:

| Câmp BQM | `logical_name` în qualification bundle |
|---|---|
| `release_build_definition_envelope_hash` | `release-build-definition-dsse` |
| `build_recipe_hash` | `build-recipe` |
| `build_input_set_hash` | `build-input-set` |
| `runtime_scope_policy_map_hash` | `runtime-scope-policy-map` |
| `expected_artifact_catalog_hash` | `expected-artifact-catalog` |
| `image_lock_hash` | `image-lock` |
| `qualification_policy_map_hash` | `qualification-policy-map` |
| `sbom_hash` | `sbom-index` |
| `license_report_hash` | `license-report` |
| `patch_ledger_report_hash` | `patch-ledger-report` |
| `provenance_report_hash` | `provenance-report` |
| `provenance_evidence_bundle_index_hash` | `provenance-evidence-bundle-index` |
| `surface_mode_report_hash` | `surface-mode-report` |
| `capability_catalog_hash` | `capability-catalog` |
| `capability_disposition_report_hash` | `capability-disposition-report` |
| `capability_evidence_bundle_index_hash` | `capability-evidence-bundle-index` |
| `vulnerability_report_hash` | `vulnerability-report` |
| `upstream_test_report_hash` | `upstream-test-report` |
| `ce_boundary_report_hash` | `ce-boundary-report` numai pentru `ce` |
| `ee_inventory_report_hash` | `ee-inventory-report` numai pentru `ee` |

Fiecare câmp non-null este exact digestul entry-ului cu acel logical name.
Payloadul din release-definition envelope are aceleași commits, suprafață,
recipe/input/catalog și qualification policy map ca BQM, iar `usage_mode` este
în allowed modes; digestul `runtime_scope_policy_map` este exact câmpul BQM, iar
expected catalogul are exact același `build_recipe_hash`.
`baseline_manifest_hash` din release definition, BQM, runtime scope map și
qualification policy map este identic cu pinul extern al release-ului.
Fiecare report are `subject_artifact_set_hash`, `onyx_commit`, `onyx_surface`
și `usage_mode` exact egale cu BQM; `policy_digest` este exact valoarea rolului
din `qualification-policy-map`, al cărui baseline manifest/policy snapshot este
fixat extern buildului. Orice discrepanță invalidează întregul BQM, chiar dacă
raportul și indexul ar fi fiecare valid separat.

```yaml
QualificationPolicyMap:
  schema_version: const "pmorg.qualification-policy-map/v1"
  baseline_manifest_hash: "sha256:<hex>"
  entries: nonempty sorted array[{report_role: string, policy_digest: "sha256:<hex>"}]
  entry_count: int64
```

Rolurile sunt unice, count-ul este lungimea array-ului și fiecare policy
digest rezolvă la bytes prin verification material-ul fixat; buildul nu poate
furniza un policy alternativ care să se auto-autorizeze.

Toate rapoartele de calificare au envelope-ul minim:

```yaml
QualificationReport:
  schema_version: string
  report_kind: string
  subject_artifact_set_hash: "sha256:<hex>"
  onyx_commit: full_git_sha
  onyx_surface: enum[ce, ee]
  usage_mode: enum[development_test, production]
  policy_digest: "sha256:<hex>"
  tool_name: string
  tool_version: string
  tool_artifact_digest: "sha256:<hex>"
  tool_config_hash: "sha256:<hex>"
  input_snapshot_set_hash: "sha256:<hex>"
  input_bundle_index_hash: "sha256:<hex>"
  expected_item_count: int64
  observed_item_count: int64
  missing_item_count: int64
  duplicate_item_count: int64
  verdict: enum[pass, fail]
  evidence_bundle_index_hash: "sha256:<hex>"
```

Schemele specializate extind acest envelope. `surface-mode-report` cere zero
artefacte cu axe lipsă/mismatch și zero terminologie legacy; `ce-boundary`
cere scan coverage exact și zero fișiere/importuri/layers EE;
`ee-inventory` cere egalitate între inventarul EE așteptat și observat și zero
elemente missing/unlicensed/unresolved; SBOM/license/patch/vulnerability cer
coverage exact și zero unknown/incompatible/untriaged Critical-or-High;
`patch-ledger-report` include și boundary scan-ul peste rădăcinile de ownership:
fiecare schimbare upstream este într-un seam allowlisted și apare exact o dată
în ledger, iar sub rădăcinile upstream există zero module, reguli ori tipuri de
domeniu PMORG;
`upstream-test-report` cere toate testele selectate trecute, iar orice excludere
are waiver versionat inclus ca evidence. Capability și provenance au schemele
suplimentare din §1.5–1.6. Un `verdict=pass` fără aceste invariante este invalid.
Timpii, run IDs, hostul și duration apar numai într-un execution envelope
separat; scanner DB, advisory snapshot, suite manifest și orice input care
poate schimba rezultatul intră în `input_snapshot_set_hash`.

Payloadul semnat al calificării este:

```yaml
schema_version: const "pmorg.build-qualification-attestation/v1"
build_manifest_hash: "sha256:<hex>"
artifact_set_hash: "sha256:<hex>"
qualification_bundle_index_hash: "sha256:<hex>"
valid_from: rfc3339_utc
valid_until: rfc3339_utc
next_revalidation_at: rfc3339_utc
trusted_clock_id: string
trusted_time_receipt_envelope: EvidenceArtifactRef
temporal_policy: TemporalPolicyBinding
revocation_status: EvidenceArtifactRef
verification_material_bundle: EvidenceArtifactRef
verifier_identity: string
verification_policy_hash: "sha256:<hex>"
issued_at: rfc3339_utc
```

Manifestul, payloadul și DSSE envelope-ul sunt OCI referrers/artefacte
detașate distribuite alături de setul deployabil. Validitatea atestării este
evaluată cu receipt-ul și politica temporală definite în §1.2 și cu
invariantele temporale din §1.3. Întreaga fereastră BQA este inclusă în
fereastra fiecărui `DeviationDecisionPayload` contributor, indiferent dacă
este ADR sau waiver; `next_revalidation_at` și `valid_until` efective sunt cel
mult minimul tuturor deadline-urilor de revalidare/expirare din acele decizii,
report input snapshots, revocation snapshots și verification material care au
contribuit la PASS. Admission-ul refuză o atestare not-yet-valid, expirată,
revocată ori cu revalidare restantă, chiar dacă manifestul rămâne
content-addressed valid. `build_manifest_hash` este digestul extern al BQM,
iar `artifact_set_hash` și `qualification_bundle_index_hash` sunt exact
câmpurile omoloage din acel BQM; orice mismatch invalidează DSSE-ul ca dovadă
pentru build. Două builduri curate
independente din aceleași inputuri trebuie să producă aceiași descriptori în
aceeași ordine și aceleași `artifact_set_hash`, `image_lock_hash`,
`qualification_bundle_index_hash` și build-manifest payload hash; numai
payloadul de attestation, envelope-ul, semnătura, receipt-urile și ferestrele
sale temporale pot diferi.

### 1.2 Deployment payload, target descriptor și measurement attestation

Timpul trusted este evidence semnată, nu un timestamp declarat:

```yaml
TrustedTimeReceiptPayload:
  schema_version: const "pmorg.trusted-time-receipt/v1"
  trusted_clock_id: string
  clock_source_id: string
  sequence: int64
  previous_receipt_envelope_hash: "sha256:<hex>" | null
  observed_at: rfc3339_utc
  uncertainty_seconds: int64
  monotonic_counter: int64
  source_evidence_bundle: EvidenceArtifactRef
  verification_material_bundle: EvidenceArtifactRef
  verification_policy_hash: "sha256:<hex>"
  verifier_identity: string
  issued_at: rfc3339_utc

TemporalPolicyBinding:
  policy_hash: "sha256:<hex>"
  max_clock_skew_seconds: int64
  max_time_receipt_age_seconds: int64
  max_measurement_age_seconds: int64
  max_validity_seconds: int64
  max_revalidation_interval_seconds: int64
```

Time receipt-ul are DSSE envelope separat. Policy binding-ul este copiat din
policy snapshot-ul fixat de baseline și verificat prin egalitate; workloadul nu
își poate mări limitele. Sequence și monotonic counter cresc strict, previous
receipt hash rezolvă envelope-ul precedent ca bytes offline și formează un lanț
fără gap/fork/rollback, iar uncertainty este nenegativă și
nu depășește nici clock skew-ul, nici policy maximum. Receipt-ul curent există
ca bytes offline și nu este mai vechi decât `max_time_receipt_age_seconds` la
decizie; `observed_at <= issued_at <= now+uncertainty`, iar vârsta conservatoare
`(now-uncertainty)-observed_at` este nenegativă și în limita policy.

Platforma măsoară separat bytes-ii/imaginile efectiv instalate și rulate:

```yaml
DeploymentPayloadDescriptor:
  schema_version: const "pmorg.deployment-payload-descriptor/v1"
  deployment_scope_policy_hash: "sha256:<hex>"
  artifact_descriptors: nonempty array[ArtifactDescriptor]
  artifact_count: int64
  expected_artifact_count: int64
  missing_artifact_count: int64
  unexpected_artifact_count: int64
  duplicate_artifact_key_count: int64
  runtime_workload_spec_hash: "sha256:<hex>"
  runtime_binding_set_hash: "sha256:<hex>"
  deployment_payload_fingerprint: "sha256:<hex>"
```

Descriptorii sunt reconstruiți din OCI/runtime/package APIs trusted și din
bytes-ii instalați, nu din taguri, labels ori environment variables. Ei sunt
byte-identici și în aceeași ordine cu setul cerut de BQM/deployment policy;
count-urile sunt exacte și PASS cere zero missing/unexpected/duplicate.
`deployment_scope_policy_hash` este exact entry-ul `deployment_runtime` din
`RuntimeScopePolicyMap` semnat de release definition;
nu este ales de caller, iar expected artifact set este cel autorizat de map.
`deployment_payload_fingerprint` este hash-ul RFC 8785 peste descriptorii,
workload spec și runtime bindings, nu peste obiectul care conține fingerprintul.
Descriptorul complet are un digest extern separat. La deploy, startup și
revalidation se reconstruiește; un payload necalificat nu poate folosi BQM-ul
altui build.

Descriptorul conține exclusiv identificatori opaci/HMAC și hash-uri de seturi
sortate; nu conține nume de client, secrets ori endpointuri brute:

```yaml
schema_version: const "pmorg.deployment-target-descriptor/v1"
target_uid_hmac: "hmac-sha256:<hex>"
workload_identity_set_hash: "sha256:<hex>"
organization_binding_set_hash: "sha256:<hex>"
data_binding_set_hash: "sha256:<hex>"
identity_provider_set_hash: "sha256:<hex>"
channel_binding_set_hash: "sha256:<hex>"
secret_binding_set_hash: "sha256:<hex>"
network_policy_hash: "sha256:<hex>"
resource_classification_report_hash: "sha256:<hex>"
production_resource_count: int64
unknown_resource_count: int64
derived_target_class: enum[synthetic_sandbox, client]
```

`target_fingerprint` este SHA-256 peste descriptorul RFC 8785. Clasa
`synthetic_sandbox` este permisă numai când ambele count-uri sunt zero,
fiecare binding are atestare sintetică și network policy refuză endpointurile
de producție; orice necunoscut sau măsurare imposibilă derivă `client`.
Toate set/report hashes din descriptor rezolvă la bytes în
`resource_evidence_bundle`, cu cardinalități și clasificări verificabile.

Payloadul measurement attestation, semnat prin DSSE, este:

```yaml
schema_version: const "pmorg.target-measurement-attestation/v1"
deployment_payload_descriptor_hash: "sha256:<hex>"
deployment_payload_fingerprint: "sha256:<hex>"
target_descriptor_hash: "sha256:<hex>"
target_fingerprint: "sha256:<hex>"
resource_evidence_bundle: EvidenceArtifactRef
verification_material_bundle: EvidenceArtifactRef
measured_at: rfc3339_utc
issued_at: rfc3339_utc
valid_from: rfc3339_utc
valid_until: rfc3339_utc
next_revalidation_at: rfc3339_utc
trusted_clock_id: string
trusted_time_receipt_envelope: EvidenceArtifactRef
temporal_policy: TemporalPolicyBinding
verifier_identity: string
verification_policy_hash: "sha256:<hex>"
```

Verifierul de deploy, startup guard-ul și watchdog-ul reconstruiesc descriptorul din APIs
trusted ale platformei, nu din environment variables controlate de workload.
La fiecare deploy, startup și revalidare se recalculează fingerprint-ul;
imposibilitatea de măsurare, mismatch-ul ori evidence necunoscut refuză
fail-closed sau quiesce înainte de deadline.

Release evidence pentru producție este normalizată ca obiect structural
sealed; un URI, boolean ori label liber nu este suficient:

```yaml
CeReleaseAuthorizationBinding:
  schema_version: const "pmorg.ce-release-authorization-binding/v1"
  release_id: string
  issuer_identity: string
  release_evidence: EvidenceArtifactRef
  permitted_onyx_surface: const ce
  permitted_usage_mode: const production
  permitted_operations: nonempty array[enum[deploy, startup, registry_publish, artifact_export]]
  artifact_scope_policy_hash: "sha256:<hex>"
  target_destination_scope_policy_hash: "sha256:<hex>"
  valid_from: rfc3339_utc
  valid_until: rfc3339_utc
  next_revalidation_at: rfc3339_utc
  trusted_clock_id: string
  trusted_time_receipt_envelope: EvidenceArtifactRef
  temporal_policy: TemporalPolicyBinding
  revocation_status: EvidenceArtifactRef
  verification_policy_hash: "sha256:<hex>"
  verification_material_bundle: EvidenceArtifactRef
  issued_at: rfc3339_utc

EnterpriseAuthorizationBinding:
  schema_version: const "pmorg.enterprise-authorization-binding/v1"
  authorization_id_hmac: "hmac-sha256:<hex>"
  issuer_identity: string
  authorization_evidence: EvidenceArtifactRef
  authorized_entity_hmac: "hmac-sha256:<hex>"
  seat_scope_hash: "sha256:<hex>"
  agreement_hash: "sha256:<hex>"
  permitted_onyx_surface: const ee
  permitted_usage_mode: const production
  permitted_operations: nonempty array[enum[deploy, startup, registry_publish, artifact_export]]
  artifact_scope_policy_hash: "sha256:<hex>"
  target_destination_scope_policy_hash: "sha256:<hex>"
  valid_from: rfc3339_utc
  valid_until: rfc3339_utc
  next_revalidation_at: rfc3339_utc
  trusted_clock_id: string
  trusted_time_receipt_envelope: EvidenceArtifactRef
  temporal_policy: TemporalPolicyBinding
  revocation_status: EvidenceArtifactRef
  verification_policy_hash: "sha256:<hex>"
  verification_material_bundle: EvidenceArtifactRef
  issued_at: rfc3339_utc
```

Bytes-ii autorizării, issuer chain-ul și policy snapshot-ul sunt obligatorii
offline, iar fereastra sa trebuie să includă integral fereastra admission-ului.
Operația, artifact set-ul și target/destination binding-ul trebuie permise de
scope-urile fixate. Pentru operația guvernată,
`artifact_scope_policy_hash == RuntimeScopePolicyMap.scope_policy_hash`, iar
`target_destination_scope_policy_hash` este exact schema hash din același
entry; operația apare în `permitted_operations`. Revalidation moștenește aceste
egalități de la operația părinte. Un câmp necunoscut ori mismatch refuză. Acest obiect
normalizează dovada pentru policy enforcement, fără a crea el însuși licența.

### 1.3 `DeploymentAdmissionRecord`

Payloadul recordului, semnat printr-un envelope DSSE separat, este:

```yaml
schema_version: const "pmorg.deployment-admission/v1"
admission_id: uuidv7
governed_operation: enum[deploy, startup]
artifact_set_hash: "sha256:<hex>"
build_manifest_hash: "sha256:<hex>"
build_attestation_envelope_hash: "sha256:<hex>"
deployment_payload_descriptor_hash: "sha256:<hex>"
deployment_payload_fingerprint: "sha256:<hex>"
onyx_surface: enum[ce, ee]
usage_mode: enum[development_test, production]
target_descriptor_hash: "sha256:<hex>"
target_fingerprint: "sha256:<hex>"
target_measurement_envelope_hash: "sha256:<hex>"
target_class: enum[synthetic_sandbox, client] # server-set
admission_basis: enum[synthetic_environment, ce_release, onyx_enterprise_authorization]
ce_release_authorization: CeReleaseAuthorizationBinding | null
enterprise_authorization: EnterpriseAuthorizationBinding | null
valid_from: rfc3339_utc
valid_until: rfc3339_utc
trusted_clock_id: string
trusted_time_receipt_envelope: EvidenceArtifactRef
temporal_policy: TemporalPolicyBinding
revocation_status: EvidenceArtifactRef
next_revalidation_at: rfc3339_utc
verifier_identity: string
verification_policy_hash: "sha256:<hex>"
verification_material_bundle: EvidenceArtifactRef
verifier_receipt: EvidenceArtifactRef
issued_at: rfc3339_utc
```

Matricea normativă este exhaustivă:

| Suprafață | Mod | Target | Basis | Cerință suplimentară |
|---|---|---|---|---|
| `ce` | `development_test` | `synthetic_sandbox` | `synthetic_environment` | environment measurement valid |
| `ee` | `development_test` | `synthetic_sandbox` | `synthetic_environment` | environment measurement + EE inventory |
| `ce` | `production` | `client` | `ce_release` | CE release authorization structural valid |
| `ee` | `production` | `client` | `onyx_enterprise_authorization` | Enterprise authorization, entity, seats/scope, agreement |

Celulele de clasă opusă sunt refuzuri explicite, nu cazuri neenumerate:

| Suprafață | Mod | Target observat | Verdict |
|---|---|---|---|
| `ce` | `development_test` | `client` | deny |
| `ee` | `development_test` | `client` | deny |
| `ce` | `production` | `synthetic_sandbox` | deny |
| `ee` | `production` | `synthetic_sandbox` | deny |

Orice basis, authorization object, surface/mode ori target în afara rândului
PASS exact este de asemenea deny; modul `production` nu poate fi folosit pentru
a ocoli politica development/test pe o țintă sintetică.

Pentru ambele rânduri `development_test`, ambele authorization objects sunt
null. Pentru `ce + production`, numai `ce_release_authorization` este non-null;
pentru `ee + production`, numai `enterprise_authorization` este non-null și
concordant cu organization binding-ul măsurat, entity, seats/scope și
agreement. Recordul dovedește existența unei autorizări acceptate de policy,
nu emite el însuși drepturi juridice. Recordul complet este sealed/private;
manifestul public conține numai envelope hash, verdict și cod de refuz.

Admission-ul rezolvă bytes-ii BQM, build attestation, deployment payload
descriptor, target descriptor și target measurement. `build_manifest_hash`,
`artifact_set_hash`, surface/mode și qualification bundle sunt identice în
lanțul BQM–attestation–admission; payload descriptor hash/fingerprint și target
descriptor hash/fingerprint sunt identice în measurement, admission și
reconstrucția curentă. `governed_operation` este permisă de authorization și
folosește entry-ul `deployment_runtime`; recordurile sunt distincte per
operație/deployment/target/payload. Orice diferență este deny înainte de efect.

Pentru orice fereastră temporală din acest contract se aplică simultan:

- `valid_from <= next_revalidation_at <= valid_until`;
- toate limitele din `temporal_policy` sunt nenegative și egale cu snapshot-ul
  fixat; `valid_until-valid_from <= max_validity_seconds`, iar intervalul până
  la revalidation nu depășește `max_revalidation_interval_seconds`;
- pentru measurements, `measured_at <= issued_at` și vârsta măsurării nu
  depășește `max_measurement_age_seconds`;
- `trusted_time_receipt_envelope` rezolvă payload + DSSE offline, are același
  clock ID, ordering valid și vârstă cel mult `max_time_receipt_age_seconds`;
- ceasul trusted furnizează `now` și uncertainty, iar uncertainty nu depășește
  `temporal_policy.max_clock_skew_seconds`;
- niciun timp semnat nu este future-dated: pentru measurement,
  `measured_at <= now-uncertainty` și vârsta conservatoare
  `(now-uncertainty)-measured_at` este în `[0,max_measurement_age_seconds]`;
  pentru orice payload, `issued_at <= now+uncertainty`; pentru use receipt,
  `verified_at <= issued_at <= now+uncertainty`;
- intervalul conservator `[now - uncertainty, now + uncertainty]` trebuie să
  fie integral în `[valid_from, min(next_revalidation_at, valid_until))`;
- build-qualification attestation window-ul și authorization window-ul
  aplicabil includ integral admission window-ul;
- la `min(next_revalidation_at, valid_until)`, lipsa ceasului, a revocation
  check-ului ori a revalidării declanșează watchdog-ul și quiesce/deny înainte
  de deadline; un workload deja pornit nu poate continua protejat după el.

Fiecare verificare produce un payload semnat separat:

```yaml
AdmissionUseReceiptPayload:
  schema_version: const "pmorg.admission-use-receipt/v1"
  use_id: uuidv7
  verification_event: enum[deploy, startup, watchdog_revalidation, registry_publish, artifact_export, transfer_revalidation]
  governed_operation: enum[deploy, startup, registry_publish, artifact_export]
  admission_envelope_hash: "sha256:<hex>"
  actual_payload_descriptor_hash: "sha256:<hex>"
  actual_payload_fingerprint: "sha256:<hex>"
  actual_target_or_destination_descriptor_hash: "sha256:<hex>"
  actual_target_or_destination_fingerprint: "sha256:<hex>"
  trusted_time_receipt_envelope: EvidenceArtifactRef
  revocation_check: EvidenceArtifactRef
  verification_policy_hash: "sha256:<hex>"
  verification_material_bundle: EvidenceArtifactRef
  verifier_identity: string
  verified_at: rfc3339_utc
  issued_at: rfc3339_utc
  verdict: enum[allow, deny, quiesce, abort]
  denial_reason: string | null
```

Receipt-ul are DSSE envelope și leagă descriptorii recomputați, nu valori
declarate de workload. Pentru evenimentele directe, `governed_operation` este
operația însăși; `watchdog_revalidation` moștenește `deploy|startup` din
deployment admission, iar `transfer_revalidation` moștenește
`registry_publish|artifact_export` din distribution admission. Authorization
și `RuntimeScopePolicyMap` se verifică pe acea operație părinte; un receipt nu
poate selecta alt scope. Watchdog-ul rulează independent de traficul aplicației
și înainte de deadline; dacă nu poate emite `allow`, oprește/quiesce workloadul
și refuză Odoo/MCP/channel/background effects până la un admission nou valid.
Publish/export revalidează periodic conform policy și înainte de commit; dacă
transferul ar traversa deadline-ul ori o revalidare eșuează, îl abortă și nu
face vizibili bytes parțiali.

La deploy și startup se verifică DSSE, toate evidence bytes, trusted time,
trust root, revocation, build și target. Există un record distinct per
deployment/target, stocat content-addressed ca pereche payload + DSSE sub
`deployments/<target_fingerprint>/<admission_id>/`. Testele folosesc numai
fixtures și credențiale sintetice, inclusiv pentru simularea celulelor
`production`.

### 1.4 Distribution payload, destination measurement și admission

Publicarea în registry și exportul sunt operații separate de deploy. Bytes
efectiv distribuiți sunt fixați ca subset exact al buildului calificat:

```yaml
DistributionPayloadDescriptor:
  schema_version: const "pmorg.distribution-payload-descriptor/v1"
  operation: enum[registry_publish, artifact_export]
  distribution_scope_policy_hash: "sha256:<hex>"
  expected_artifact_id_set_hash: "sha256:<hex>"
  expected_release_metadata_role_set_hash: "sha256:<hex>"
  deployable_artifact_descriptors: nonempty array[ArtifactDescriptor]
  deployable_artifact_count: int64
  expected_deployable_artifact_count: int64
  missing_deployable_artifact_count: int64
  unexpected_deployable_artifact_count: int64
  duplicate_deployable_artifact_key_count: int64
  release_metadata_bundle_index_hash: "sha256:<hex>"
  release_metadata_entry_count: int64
  expected_release_metadata_entry_count: int64
  missing_release_metadata_count: int64
  unexpected_release_metadata_count: int64
  duplicate_release_metadata_count: int64
  distribution_payload_hash: "sha256:<hex>"
```

Primul array are aceeași ordine/cheie unică din §1.1; fiecare descriptor trebuie
să apară byte-identic în `BuildQualificationManifest`, iar count-ul este
lungimea array-ului și este egal cu subsetul permis de policy. Artefactele
detașate pe care BQM le exclude din setul deployabil — BQM, attestation
payload/DSSE, qualification/evidence indexes și rapoartele cerute — sunt
inventariate separat într-un `EvidenceBundleIndex` cu
`bundle_kind=release_metadata`; setul exact de logical roles este derivat din
`distribution_scope_policy_hash` și din
[lista RC](12-ACCEPTANCE-TRACEABILITY.md#12-artefactele-obligatorii-ale-unui-release-candidate).
PASS cere pentru ambele seturi zero
missing/unexpected/duplicate.

`distribution_scope_policy_hash`, expected artifact IDs și expected release
metadata roles sunt exact entry-ul `registry_publish|artifact_export` al
operației părinte din `RuntimeScopePolicyMap` semnat;
callerul nu le poate reduce ori substitui. Scope-urile din CE/Enterprise
authorization trebuie să fie egale cu artifact policy-ul release-ului și să
treacă schema target/destination autorizată de același map; pot restrânge
entitatea/operațiile, dar nu pot micșora setul de bytes obligatoriu.

La publish/export, gateway-ul reconstruiește descriptorii și metadata indexul
din bytes efectivi și refuză scope-policy mismatch, missing, unexpected,
duplicate ori digest mismatch. `distribution_payload_hash` este SHA-256 peste
obiectul RFC 8785
`{deployable_artifact_descriptors, release_metadata_bundle_index_hash}`, nu
peste descriptorul care conține acest câmp;
`distribution_payload_descriptor_hash` este digestul extern al întregului
descriptor persistat.

Destinația este măsurată, nu declarată de apelant:

```yaml
DistributionDestinationDescriptor:
  schema_version: const "pmorg.distribution-destination-descriptor/v1"
  destination_uid_hmac: "hmac-sha256:<hex>"
  operation: enum[registry_publish, artifact_export]
  registry_or_gateway_identity_set_hash: "sha256:<hex>"
  account_binding_set_hash: "sha256:<hex>"
  organization_binding_set_hash: "sha256:<hex>"
  authorized_entity_binding_set_hash: "sha256:<hex>"
  seat_scope_binding_set_hash: "sha256:<hex>"
  agreement_binding_set_hash: "sha256:<hex>"
  endpoint_and_storage_policy_hash: "sha256:<hex>"
  resource_classification_report_hash: "sha256:<hex>"
  production_destination_count: int64
  unknown_destination_count: int64
  derived_destination_class: enum[controlled_synthetic_registry, client_destination]

DistributionDestinationMeasurementAttestation:
  schema_version: const "pmorg.distribution-destination-measurement/v1"
  destination_descriptor_hash: "sha256:<hex>"
  destination_fingerprint: "sha256:<hex>"
  destination_evidence_bundle: EvidenceArtifactRef
  verification_material_bundle: EvidenceArtifactRef
  measured_at: rfc3339_utc
  issued_at: rfc3339_utc
  valid_from: rfc3339_utc
  valid_until: rfc3339_utc
  next_revalidation_at: rfc3339_utc
  trusted_clock_id: string
  trusted_time_receipt_envelope: EvidenceArtifactRef
  temporal_policy: TemporalPolicyBinding
  verifier_identity: string
  verification_policy_hash: "sha256:<hex>"
```

`destination_fingerprint` este hash-ul RFC 8785 al descriptorului.
`controlled_synthetic_registry` cere zero production/unknown, bindinguri
sintetice atestate și policy care refuză endpoints/storage de producție;
unknown sau măsurare imposibilă derivă `client_destination`. Gateway-ul
reconstruiește descriptorul din API-urile trusted ale registry/storage/export
providerului; toate set/report hashes rezolvă la bytes în
`destination_evidence_bundle`. După rezolvarea autentificării și a oricărui
redirect, gateway-ul reconstruiește din nou descriptorul și recalculează
fingerprint-ul imediat înainte de primul byte; orice schimbare oprește operația.

Payloadul admission, semnat separat prin DSSE, este:

```yaml
schema_version: const "pmorg.distribution-admission/v1"
admission_id: uuidv7
operation: enum[registry_publish, artifact_export]
artifact_set_hash: "sha256:<hex>"
build_manifest_hash: "sha256:<hex>"
build_attestation_envelope_hash: "sha256:<hex>"
distribution_payload_descriptor_hash: "sha256:<hex>"
distribution_payload_hash: "sha256:<hex>"
onyx_surface: enum[ce, ee]
usage_mode: enum[development_test, production]
destination_descriptor_hash: "sha256:<hex>"
destination_fingerprint: "sha256:<hex>"
destination_measurement_envelope_hash: "sha256:<hex>"
destination_class: enum[controlled_synthetic_registry, client_destination] # server-set
admission_basis: enum[synthetic_environment, ce_release, onyx_enterprise_authorization]
ce_release_authorization: CeReleaseAuthorizationBinding | null
enterprise_authorization: EnterpriseAuthorizationBinding | null
valid_from: rfc3339_utc
valid_until: rfc3339_utc
next_revalidation_at: rfc3339_utc
trusted_clock_id: string
trusted_time_receipt_envelope: EvidenceArtifactRef
temporal_policy: TemporalPolicyBinding
revocation_status: EvidenceArtifactRef
verifier_identity: string
verification_policy_hash: "sha256:<hex>"
verification_material_bundle: EvidenceArtifactRef
verifier_receipt: EvidenceArtifactRef
issued_at: rfc3339_utc
```

Matricea este aceeași, exhaustivă, ca la deployment: ambele
`development_test` permit numai `controlled_synthetic_registry` cu basis
`synthetic_environment`; `ce + production` cere `client_destination +
ce_release` și numai `ce_release_authorization` non-null; `ee + production`
cere `client_destination +
onyx_enterprise_authorization`, iar obiectul structural de authorization este
non-null, concordant cu bindingurile măsurate ale destinației și permite
operația. În ambele `development_test`, ambele obiecte sunt null; în fiecare
celulă production, obiectul celeilalte suprafețe este null.

Refuzurile explicite sunt ambele `development_test + client_destination` și
ambele `production + controlled_synthetic_registry`, plus orice basis,
authorization, operation, payload ori destinație care nu corespunde rândului
PASS exact.

Orice combinație invalidă, destination/payload recomputation mismatch,
unknown/unmeasurable, DSSE/evidence lipsă, not-yet-valid, expired, revoked,
missed revalidation ori trusted-clock failure refuză înainte de publish/export.
Recordurile sunt distincte per operație/destinație/payload și se păstrează ca
payload + DSSE sub
`distributions/<destination_fingerprint>/<admission_id>/`.

Admission-ul rezolvă bytes-ii BQM, build attestation, distribution payload
descriptor, destination descriptor și destination measurement. Build/artifact
set/surface/mode, payload hash și descriptor/destination hashes/fingerprints
sunt exact egale de-a lungul lanțului și cu reconstrucția curentă; `operation`
este permisă de authorization și selectează exact entry-ul omolog din runtime
scope map. Orice diferență refuză înainte de primul byte.

### 1.5 Capability disposition

```yaml
ContentAddressedSourceRef:
  repository: uri
  commit: full_git_sha
  paths: nonempty array[string]
  tree_hash: "sha256:<hex>"
  source_snapshot: EvidenceArtifactRef

SourceScopeManifest:
  schema_version: const "pmorg.source-scope-manifest/v1"
  repository: uri
  commit: full_git_sha
  scope_kind: enum[pmorg, onyx_ce, onyx_ee]
  roots: nonempty array[string]
  tree_hash: "sha256:<hex>"
  path_inventory: EvidenceArtifactRef
  derivation_policy_hash: "sha256:<hex>"
  generator_identity: string
  generator_artifact_digest: "sha256:<hex>"
  derivation_evidence_bundle: EvidenceArtifactRef
  expected_path_count: int64
  duplicate_path_count: int64
  unreadable_path_count: int64

TestEvidence:
  test_id: string
  test_manifest: EvidenceArtifactRef
  result: EvidenceArtifactRef
  verdict: enum[pass, fail]

CandidateQualificationReport:
  schema_version: const "pmorg.candidate-qualification-report/v1"
  catalog_hash: "sha256:<hex>"
  capability_id: string
  candidate_id: string
  source_ref: ContentAddressedSourceRef
  qualification_policy: EvidenceArtifactRef
  required_test_manifest: EvidenceArtifactRef
  expected_test_count: int64
  executed_test_count: int64
  missing_test_count: int64
  duplicate_test_count: int64
  failed_test_count: int64
  test_evidence: nonempty array[TestEvidence]
  verdict: enum[pass, fail]

OnyxCapabilityCandidate:
  candidate_id: string
  source_ref: ContentAddressedSourceRef
  onyx_surface: enum[ce, ee]
  license_class: enum[mit-expat, onyx-enterprise, third-party]
  qualification: enum[pass, fail]
  qualification_report: CandidateQualificationReport

CandidateSearchEvidence:
  schema_version: const "pmorg.candidate-search-evidence/v1"
  search_id: string
  catalog_hash: "sha256:<hex>"
  capability_id: string
  searched_surfaces: nonempty array[enum[ce, ee]]
  source_scopes: nonempty array[SourceScopeManifest]
  search_spec_version: semver
  search_tool_name: string
  search_tool_version: semver
  search_tool_artifact_digest: "sha256:<hex>"
  expected_path_count: int64
  scanned_path_count: int64
  unscanned_path_count: int64
  duplicate_path_count: int64
  unreadable_path_count: int64
  raw_hit_count: int64
  candidate_ids: array[string]
  rejected_hit_count: int64
  classification_record_count: int64
  unclassified_hit_count: int64
  duplicate_hit_id_count: int64
  query_plan: EvidenceArtifactRef
  raw_results: EvidenceArtifactRef
  hit_classification: EvidenceArtifactRef

PostDispositionQualificationReport:
  schema_version: const "pmorg.post-disposition-qualification/v1"
  catalog_hash: "sha256:<hex>"
  capability_id: string
  implementation_path_set_hash: "sha256:<hex>"
  patch_ledger_set_hash: "sha256:<hex>"
  required_test_manifest: EvidenceArtifactRef
  expected_test_count: int64
  executed_test_count: int64
  missing_test_count: int64
  duplicate_test_count: int64
  failed_test_count: int64
  test_evidence: nonempty array[TestEvidence]
  verdict: enum[pass, fail]

ImplementationPathRef:
  path: string
  content_hash: "sha256:<hex>"
  source_ref: ContentAddressedSourceRef
  ownership_class: enum[pmorg_owned, upstream_ce_reused, upstream_ce_direct_patch, upstream_ee_reused, upstream_ee_direct_patch, third_party]
  license_class: enum[pmorg, mit-expat, onyx-enterprise, third-party]
  provenance_inventory_item: EvidenceArtifactRef

PatchLedgerRecordRef:
  ledger_entry_id: string
  path: string
  source_ref: ContentAddressedSourceRef
  base_blob_hash: "sha256:<hex>" | null
  patched_blob_hash: "sha256:<hex>" | null
  ownership_class: enum[upstream_ce_direct_patch, upstream_ee_direct_patch]
  license_class: enum[mit-expat, onyx-enterprise]
  ledger_record: EvidenceArtifactRef
  protector_tests: nonempty array[TestEvidence]

DeviationDecisionPayload:
  schema_version: const "pmorg.capability-deviation-decision/v1"
  decision_id: string
  decision_type: enum[adr, waiver]
  pmorg_spec_commit: full_git_sha
  pmorg_platform_commit: full_git_sha
  onyx_commit: full_git_sha
  onyx_surface: enum[ce, ee]
  usage_mode: enum[development_test, production]
  artifact_set_hash: "sha256:<hex>"
  catalog_version: semver
  catalog_hash: "sha256:<hex>"
  capability_id: string
  affected_candidate_ids: nonempty array[string]
  permitted_disposition: enum[patch, pmorg_independent]
  implementation_path_set_hash: "sha256:<hex>"
  patch_ledger_set_hash: "sha256:<hex>"
  post_disposition_test_manifest_hash: "sha256:<hex>"
  rationale: string
  approver_identity: string
  authority_grant: EvidenceArtifactRef
  approved_at: rfc3339_utc
  valid_from: rfc3339_utc
  valid_until: rfc3339_utc
  next_revalidation_at: rfc3339_utc
  trusted_clock_id: string
  trusted_time_receipt_envelope: EvidenceArtifactRef
  temporal_policy: TemporalPolicyBinding
  revocation_status: EvidenceArtifactRef
  verifier_identity: string
  verification_policy_hash: "sha256:<hex>"
  verification_material_bundle: EvidenceArtifactRef
  issued_at: rfc3339_utc

CapabilityCatalogItem:
  capability_id: string
  pmorg_requirement_ids: nonempty array[string]
  contract_tests: nonempty array[EvidenceArtifactRef]

CapabilityCatalog:
  schema_version: const "pmorg.capability-catalog/v1"
  catalog_version: semver
  pmorg_spec_commit: full_git_sha
  disposition_scope_rule: EvidenceArtifactRef
  applicable_requirement_set: EvidenceArtifactRef
  required_search_surfaces: nonempty array[enum[ce, ee]]
  expected_requirement_count: int64
  mapped_requirement_count: int64
  unmapped_requirement_count: int64
  unknown_requirement_count: int64
  duplicate_capability_id_count: int64
  items: nonempty array[CapabilityCatalogItem]
  item_count: int64

CapabilityDispositionRecord:
  schema_version: const "pmorg.capability-disposition/v1"
  catalog_version: semver
  catalog_hash: "sha256:<hex>"
  pmorg_spec_commit: full_git_sha
  pmorg_platform_commit: full_git_sha
  onyx_commit: full_git_sha
  artifact_set_hash: "sha256:<hex>"
  onyx_surface: enum[ce, ee]
  usage_mode: enum[development_test, production]
  capability_id: string
  pmorg_requirement_ids: nonempty array[string]
  candidate_search_outcome: enum[candidates_found, no_candidate]
  candidate_search_evidence: CandidateSearchEvidence
  candidates: array[OnyxCapabilityCandidate]
  disposition: enum[reuse, patch, pmorg_independent]
  selected_candidate_ids: array[string]
  implementation_path_set_hash: "sha256:<hex>"
  implementation_refs: nonempty array[ImplementationPathRef]
  patch_ledger_set_hash: "sha256:<hex>"
  patch_ledger_refs: array[PatchLedgerRecordRef]
  post_disposition_qualification: PostDispositionQualificationReport
  rationale: string
  deviation_decision_envelope: EvidenceArtifactRef | null
  record_evidence_bundle_index: EvidenceArtifactRef

CapabilityDispositionReport:
  schema_version: const "pmorg.capability-disposition-report/v1"
  catalog_version: semver
  pmorg_spec_commit: full_git_sha
  pmorg_platform_commit: full_git_sha
  subject_artifact_set_hash: "sha256:<hex>"
  onyx_surface: enum[ce, ee]
  usage_mode: enum[development_test, production]
  catalog_hash: "sha256:<hex>"
  catalog_item_count: int64
  catalog_requirement_count: int64
  record_refs: nonempty array[EvidenceArtifactRef]
  record_count: int64
  covered_count: int64
  missing_count: int64
  duplicate_count: int64
  unmapped_requirement_count: int64
  unknown_requirement_count: int64
  requirement_ref_mismatch_count: int64
  dangling_evidence_count: int64
  records_and_evidence_bundle_index: EvidenceArtifactRef
```

Invariante:

- catalogul este derivat prin regula fixată din setul cerințelor aplicabile;
  PASS cere `expected_requirement_count=mapped_requirement_count`, item count
  egal cu lungimea array-ului și zero unmapped/unknown/duplicate; micșorarea
  catalogului nu poate transforma o cerință nemapată în coverage 100%;
- `CapabilityDispositionReport.catalog_hash` este digestul exact al catalogului,
  iar `catalog_version` și `pmorg_spec_commit` sunt identice în catalog, report
  și fiecare record. Fiecare record are `pmorg_platform_commit`, `onyx_commit`,
  `artifact_set_hash`, `onyx_surface` și `usage_mode` exact egale cu reportul
  (inclusiv câmpurile moștenite din `QualificationReport`) și cu BQM; un record
  pentru alt build, commit, surface ori mode este dangling/invalid, nu coverage;
- catalog item-ul și disposition record-ul cu același `capability_id` au
  exact aceleași `pmorg_requirement_ids`; test manifestul calificării este
  exact setul `contract_tests` al itemului și fiecare protector test are result
  bytes;
- fiecare `SourceScopeManifest` este derivat din tree-ul Git fixat independent
  de scanner; uniunea lui dă denominatorul search. PASS cere suprafețele exact
  egale cu `required_search_surfaces`, expected=scanned și zero
  unscanned/duplicate/unreadable;
- fiecare scope `onyx_ce|onyx_ee` are repository-ul canonic din baseline și
  `commit == record.onyx_commit == QualificationReport.onyx_commit ==
  BuildQualificationManifest.onyx_commit`; tree/roots/path inventory sunt
  derivate din exact acel commit conform `disposition_scope_rule`. Fiecare
  candidate `source_ref` are același repository/commit, paths integral în
  scope-ul suprafeței declarate și snapshot bytes conforme; alt tree/commit
  produce `INVALID`, chiar dacă scanarea sa este intern completă;
- candidate search folosește numai `onyx_ce|onyx_ee`, în bijecție cu
  `searched_surfaces`; provenance folosește `pmorg_source_scope.scope_kind=pmorg`
  și `ee_source_scope.scope_kind=onyx_ee`;
- search evidence are același `catalog_hash` și `capability_id` ca recordul;
  source scope derivation policy/generator/evidence sunt fixate și verificabile
  offline;
- `raw_hit_count = len(candidate_ids) + rejected_hit_count =
  classification_record_count`, cu zero unclassified/duplicate IDs; fiecare raw
  hit este candidat ori respins explicit cu motiv în classification bytes;
- `candidates=[]` este valid numai cu `candidate_search_outcome=no_candidate`,
  `candidate_ids=[]` și search coverage complet; `candidates_found` cere array
  non-gol. Acces/corpus incomplet produce `INVALID`, nu `no_candidate`;
- setul `candidates[*].candidate_id` este exact candidate IDs din search;
- candidate qualification execută exact contract tests/policy fixate: counts
  satisfac `expected=executed=len(test_evidence)`, zero missing/duplicate, iar
  failed count este exact numărul rezultatelor fail; `pass` iff zero failed,
  iar `fail` iff minimum un test obligatoriu a eșuat. Un hit neaplicabil este respins în search
  classification, nu retrogradat arbitrar ca candidat;
- pentru fiecare candidat, outer/report `candidate_id` și `source_ref` sunt
  exact egale, reportul are catalog/capability egale cu recordul, iar
  `candidate.qualification = qualification_report.verdict`;
- candidate IDs sunt unice, iar `selected_candidate_ids` este un subset unic
  al lor; un build `ce` nu poate selecta niciun candidat `ee`;
- `reuse`: cel puțin un candidat selectat are `pass`; implementation refs
  indică byte-identic sursa selectată, ownership `upstream_*_reused` pentru
  cod Onyx-owned sau `third_party` pentru candidatul third-party; patch refs
  sunt goale;
- `patch`: există candidat selectat, implementation refs și patch-ledger refs
  non-goale, iar verdictul post-patch este `pass`; patchul direct EE este
  `license_class=onyx-enterprise` și nu este PMORG-owned;
- `pmorg_independent`: selected candidate IDs și patch refs sunt goale, iar
  implementation refs sunt PMORG-owned; lipsa candidatului este demonstrată
  de search evidence, nu printr-un candidat fictiv;
- dacă există orice candidat `pass`, orice rezultat diferit de reutilizarea sa
  nemodificată cere un `deviation_decision_envelope` DSSE valid. Payloadul
  deciziei se leagă exact de spec/platform/Onyx commits, surface/mode,
  artifact, catalog version/hash, capability/candidați, dispoziție,
  hash-urile implementation/patch și post-disposition test
  manifestul, iar authority grant-ul și verification
  material există offline. `approved_at <= issued_at`, iar receipt-ul trusted,
  ordering-ul, fereastra, revocation și revalidarea trec aceleași reguli
  conservatoare din §1.3; decizia expirată, future-dated ori cu revalidare
  restantă este invalidă. Atât ADR-ul aplicat acestui build, cât și waiver-ul
  au `valid_until` nenul;
- fiecare implementation path corespunde exact unui item din provenance path
  inventory cu același path/hash/ownership/license. Fiecare direct patch
  corespunde exact unui implementation path și unui singur ledger record cu
  base/patched blob hashes și protector results; `ce` are zero ownership/licență
  EE, iar `pmorg_independent` are exclusiv `pmorg_owned`;
- matricea source/surface/license este exactă: candidat Onyx-owned
  `ce + mit-expat` cere `upstream_ce_reused + mit-expat`; candidat Onyx-owned
  din rădăcinile EE cere `upstream_ee_reused + onyx-enterprise`; un candidat
  third-party păstrează `third_party` indiferent de surface, cu source și
  license evidence. Numai codul Onyx-owned din rădăcinile EE are obligatoriu
  licență `onyx-enterprise`, iar codul Onyx-owned CE nu poate declara acea
  licență. Reuse implementation
  `source_ref` este exact source ref-ul
  candidatului selectat. Patchul moștenește suprafața/licența source ref-ului și
  corespunde ledgerului `upstream_ce_direct_patch|upstream_ee_direct_patch`;
  ledger `source_ref` este exact sursa candidatului selectat și are
  `commit == record.onyx_commit`;
  pentru EE licența este obligatoriu `onyx-enterprise`. `pmorg_owned` cere
  `license_class=pmorg`, repository-ul PMORG-Platform din baseline,
  `source_ref.commit == record.pmorg_platform_commit` și path sub rădăcinile
  PMORG-owned fixate în disposition scope rule;
- post-disposition report se leagă exact de catalog/capability și aceleași
  implementation/patch set hashes; expected=executed=len(test evidence), zero
  missing/duplicate, failed count exact, iar recordul este acceptat numai cu
  `verdict=pass` și zero failed;
- IDs, requirement refs, candidate IDs și record hashes sunt unice.

`record_refs` este sortat canonic după logical name și fiecare ref rezolvă
bytes-ii unui `CapabilityDispositionRecord`; digestul reportului rămâne extern.
PASS cere exact un record per catalog item, 100% coverage și zero
missing/duplicate/unmapped/unknown/requirement-mismatch/dangling. Nested
`record_evidence_bundle_index` conține numai dependențele recordului — source
snapshots, scope/requirement bytes, search, qualification/test results, ledger
records, decisions și protector evidence — și exclude recordul însuși.
`records_and_evidence_bundle_index` conține exact recordurile și indexurile lor,
dar exclude reportul, catalogul și propriul index. Digestul său este exact
`QualificationReport.evidence_bundle_index_hash` și
`BuildQualificationManifest.capability_evidence_bundle_index_hash`; fiecare
record ref apare exact o dată, iar graful rămâne aciclic.

### 1.6 `ProvenanceScanReport`

```yaml
ProvenancePathInventoryItem:
  path: string
  content_hash: "sha256:<hex>"
  ownership_class: enum[pmorg_owned, upstream_ce_reused, upstream_ce_direct_patch, upstream_ee_reused, upstream_ee_direct_patch, third_party]
  patch_ledger_record: EvidenceArtifactRef | null
  license_class: enum[pmorg, mit-expat, onyx-enterprise, third-party]

ProvenanceMatchRecord:
  match_id: string
  raw_match_id: string
  subject_path: string
  subject_input_content_hash: "sha256:<hex>"
  subject_final_content_hash: "sha256:<hex>" | null
  path_ownership_class: enum[pmorg_owned, upstream_ce_direct_patch, upstream_ee_direct_patch]
  upstream_ee_path: string
  upstream_ee_content_hash: "sha256:<hex>"
  match_kind: enum[exact, normalized, similarity]
  algorithm_id: string
  similarity_basis_points: int64
  resolution: enum[independent_match, licensed_patch, removed, unresolved]
  patch_ledger_record: PatchLedgerRecordRef | null
  license_class: enum[pmorg, mit-expat, onyx-enterprise, third-party]
  reviewer_identity: string
  verifier_identity: string
  resolution_evidence: nonempty array[EvidenceArtifactRef]

ProvenanceScanReport:
  schema_version: const "pmorg.provenance-scan-report/v1"
  pmorg_spec_commit: full_git_sha
  subject_artifact_set_hash: "sha256:<hex>"
  onyx_surface: enum[ce, ee]
  usage_mode: enum[development_test, production]
  scanner_name: string
  scanner_version: semver
  scanner_artifact_digest: "sha256:<hex>"
  algorithm_id: string
  normalization_spec_version: semver
  similarity_threshold_basis_points: int64
  pmorg_repository: uri
  pmorg_platform_commit: full_git_sha
  upstream_repository: uri
  upstream_commit: full_git_sha
  ee_tree_hash: "sha256:<hex>"
  pmorg_tree_hash: "sha256:<hex>"
  pmorg_source_scope: SourceScopeManifest
  ee_source_scope: SourceScopeManifest
  scan_input_path_inventory: EvidenceArtifactRef
  final_path_inventory: EvidenceArtifactRef
  expected_pmorg_path_count: int64
  scanned_pmorg_path_count: int64
  unscanned_pmorg_path_count: int64
  expected_ee_path_count: int64
  scanned_ee_path_count: int64
  unscanned_ee_path_count: int64
  unreadable_path_count: int64
  duplicate_path_count: int64
  unclassified_path_count: int64
  raw_match_records: EvidenceArtifactRef
  raw_match_count: int64
  classified_match_records: EvidenceArtifactRef
  classification_record_count: int64
  unclassified_match_count: int64
  duplicate_match_id_count: int64
  match_record_count: int64
  exact_match_count: int64
  similarity_match_count: int64
  unreviewed_match_count: int64
  invalid_licensed_patch_count: int64
  forbidden_copy_count: int64
  unresolved_count: int64
  evidence_bundle_index_hash: "sha256:<hex>"
```

Cele două `SourceScopeManifest` sunt derivate independent din commit/tree și
conțin denominatorii compleți pentru rădăcinile PMORG și EE. Scannerul nu își
poate declara singur expected counts. PASS cere egalitate expected=scanned
pentru ambele corpusuri și zero unscanned/unreadable/duplicate/unclassified.
Tree/repository/commit din manifests sunt exact cele din report, iar
`scan_input_path_inventory` este egal byte-for-byte cu uniunea scope-urilor
declarate de policy; orice path omis sau adăugat invalidează scanul.
`pmorg_repository` și `upstream_repository` sunt exact pinurile canonice din
baseline; `pmorg_platform_commit == BuildQualificationManifest.pmorg_platform_commit`,
iar `upstream_commit == QualificationReport.onyx_commit ==
BuildQualificationManifest.onyx_commit`. Scope-ul PMORG are repository/commit/
tree exact egale cu câmpurile PMORG din report, iar scope-ul EE cu câmpurile
upstream; `pmorg_spec_commit`, artifact set, surface și mode sunt exact egale
cu BQM și envelope-ul `QualificationReport`. Un report complet peste alt
commit/tree/build este `INVALID`.
`scan_input_path_inventory` și `final_path_inventory` sunt arrays complete,
sortate și unice după path, iar fiecare implementation ref din §1.5 corespunde
exact unui item final cu același hash/ownership/license.
`ProvenancePathInventoryItem.ownership_class` are exact aceleași șase valori ca
`ImplementationPathRef.ownership_class`, inclusiv ambele clase `*_reused` și
`third_party`; inventarul poate reprezenta orice disposition validă.

Raw matches sunt outputul byte-closed al scannerului peste corpusurile complete.
Classification records sunt sortate canonic după
`subject_path + upstream_ee_path + algorithm_id`, au IDs unice și sunt în
bijecție cu raw matches:
`raw_match_count=classification_record_count=match_record_count`, cu zero
unclassified/duplicate. Ele includ fiecare exact/normalized match și fiecare
similaritate peste prag. `licensed_patch` este valid exclusiv
dacă path-ul este `upstream_ee_direct_patch`, `patch_ledger_record` rezolvă unicul
owner al path-ului, ledgerul indică sursa EE și
`license_class=onyx-enterprise`; path-ul este exclus din setul PMORG-owned. Un
path PMORG-owned nu poate folosi `licensed_patch`: trebuie ori evidence pentru
`independent_match`, ori eliminare, altfel rămâne `unresolved`. Pentru un build
`ce`, numărul de `upstream_ee_direct_patch` și `licensed_patch` este zero.

Rezoluțiile sunt condiționale:

- `independent_match`: path-ul final rămâne `pmorg_owned`, patch ledger este
  null, iar evidence include subject/upstream bytes, reprezentarea normalizată,
  lineage/origin și receipt-ul review-ului care demonstrează non-copierea;
- `licensed_patch`: `PatchLedgerRecordRef` este non-null, path-ul este direct
  sub rădăcina EE fixată, base/patched hashes corespund inventarelor și
  ownership/licența rămân Onyx Enterprise;
- `removed`: subject path-ul/hash-ul din scan input nu apare în inventarul
  final, `subject_final_content_hash=null`, iar removal diff + rescan evidence
  sunt prezente;
- `unresolved`: blochează PASS.

Pragul, algoritmul, normalizarea și arborii sunt fixați în baseline manifest.
Pentru fiecare match, bundle-ul conține subject/upstream blob bytes și
reprezentarea normalizată când este aplicabilă. PASS cere toate evidence bytes
disponibile offline și zero
unreviewed/invalid-licensed-patch/forbidden-copy/unresolved. Similaritatea peste
prag este la fel de obligatorie ca exact-hash matching.
`evidence_bundle_index_hash` este exact
`BuildQualificationManifest.provenance_evidence_bundle_index_hash`, iar indexul
conține source scopes/inventories, raw/classified matches, bloburi și toate
resolution evidence, fără ref dangling.

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
