# PMORG v3 — criterii de acceptare și trasabilitate

| Câmp | Valoare |
|---|---|
| Status | Accepted |
| Baseline | `RB-1/C2` |
| Scope | MVP G3-A–G3-F |
| Data | 2026-07-19 |

## 1. Regula verdictului

Un gate are exact unul dintre verdictele:

- `PASS` — toate criteriile obligatorii au trecut;
- `FAIL` — cel puțin un criteriu al produsului a eșuat;
- `INVALID` — harness-ul, oracle isolation, run bundle sau trasarea nu permit
  un verdict valid.

`INVALID` nu devine `PASS` și nu este ascuns într-o medie. Un criteriu
structural `must` eșuat produce `FAIL` indiferent de scorul agregat.

G3-A–G3-F sunt conjunctive. MVP-ul este `PASS` numai dacă toate sunt
`PASS` pe același release candidate și pe manifestele declarate.

## 2. Repetabilitate

- fiecare test structural rulează din volume curate;
- M0 și scenariul longitudinal combinat rulează de 3 ori identic per profil
  aplicabil;
- fiecare fault case rulează separat de minimum 3 ori;
- aceeași intrare deterministă trebuie să producă același verdict, aceleași
  efecte canonice și același lanț semantic, ignorând numai IDs/timestamps
  declarate non-deterministe;
- orice abatere neexplicată este `FAIL`, nu „flakiness acceptabil”.

## 3. G3-A — fork și build

| ID test | Criteriu PASS | Prag |
|---|---|---|
| `A-FORK-001` | tagul și SHA-ul Onyx și commitul PMORG sunt fixate | 100% prezente în manifest și UI/version endpoint |
| `A-UPSTREAM-001` | suita upstream selectată trece pe baseline curat și fork | 100% teste obligatorii; excluderile au waiver versionat |
| `A-LIC-001` | build qualification este completă și content-addressed | release definition, expected catalog și policy maps sunt extern fixate și identice cu BQM; DSSE valid și temporal bounded; artifact set și qualification bundle identice cu manifestul; toate rolurile/schema obligatorii prezente; `ce`: 0 EE; orice `ee`: inventar complet; zero dangling/mismatch/unknown |
| `A-SURFACE-001` | surface claim-ul este susținut de artefact real | fiecare variantă publicată are build real al suprafeței declarate și propriul G3-A; CE nu este declarat disponibil din fixtures; MVP-ul EE nu este blocat de un release CE separat |
| `A-REPRO-001` | buildul este reproductibil | 2/2 builduri curate cu aceleași input snapshots au descriptorii în aceeași ordine și artifact-set, image-lock, qualification-bundle și toate report payload hashes identice; numai qualification-attestation/execution envelopes, receipt-urile și ferestrele temporale pot diferi |
| `A-EVIDENCE-001` | lanțul criptografic este verificabil offline | 100% payloaduri DSSE valide; 100% trust/cert/revocation/receipt/resource/authorization refs rezolvă la bytes; zero autoreferințe, dangling refs ori trust auto-autorizat |
| `A-REPORT-001` | rapoartele BQM sunt complete | 100% required roles, scheme și artifact coverage; zero missing/duplicate/dangling/unknown; zero cerințe catalog unmapped; conditional CE/EE set exact |
| `A-LIC-002` | deployment/startup/revalidation admission este fail-closed | toate 4 celulele PASS și cele 4 combinații de clasă opusă deny, inclusiv ambele `production + synthetic`; runtime scope este exact entry-ul extern `deployment_runtime`, iar operația părinte nu poate fi schimbată la watchdog; payload descriptor și target descriptor/fingerprint reconstruite separat la deploy, startup și watchdog; zero missing/unexpected/duplicate; missing, not-yet-valid, expired, revoked, overdue-revalidation, clock-skew, unknown/unmeasurable, payload/envelope/build/target mismatch și trust root sintetic ne-listat refuzate/quiesced |
| `A-LIC-003` | publish/export admission este fail-closed | toate 4 celulele PASS și cele 4 combinații de destinație opusă deny, inclusiv ambele `production + controlled_synthetic_registry`; distribution scope și metadata roles sunt entry-ul extern exact al operației părinte, care nu poate fi schimbată la revalidation; payloadul și destination descriptor/fingerprint recomputate înainte de transfer și după auth/redirect; unknown/unmeasurable, destination/principal/namespace/redirect change, replay, missing/not-yet-valid/expired/revoked/overdue/mismatch/trust root ne-listat refuzate; transfer activ revalidat și abortat înainte de deadline |
| `A-PATCH-001` | fork-ul este thin, iar diff-ul upstream este inventariat exact | fiecare cale upstream modificată apare exact o dată în patch ledger și aparține seam allowlist-ului; 0 missing/duplicate și blob hashes conforme diff-ului; 0 module/reguli/tipuri de domeniu PMORG sub rădăcini upstream-owned |
| `A-PATCH-002` | catalogul este închis peste cerințe | uniunea requirement refs este exact setul aplicabil din baseline; zero unmapped/unknown; capability IDs unice și exact un disposition record pentru 100% catalog |
| `A-PATCH-003` | candidate search și cazul no-candidate sunt demonstrabile | source scopes corespund exact repository/commit/tree pinurilor Onyx ale BQM și sunt derivate independent; expected=scanned pentru CE/EE cerute, zero unreadable/unscanned/duplicate/unclassified; raw hits = candidates + rejects; qualification execută exact contract tests; `candidates=[]` numai pentru `pmorg_independent` demonstrat; evidence incomplet sau scan pe alt commit = `INVALID` |
| `A-PATCH-004` | reuse-default nu poate fi ocolit tacit | pentru 100% recordurile cu candidat `pass`, orice `patch` ori `pmorg_independent` are ADR/waiver DSSE valid legat exact de spec/artifact/catalog/capability/candidați/disposition/implementation/ledger, authority grant și protector results; 0 decizii lipsă/expirate/replayable |
| `A-PATCH-005` | `licensed_patch` păstrează granița EE | 100% sunt patchuri directe pe căi EE, cu exact un ledger owner, upstream Onyx, licență Enterprise și blob hashes; 0 căi PMORG-owned clasificate astfel și 0 în build `ce` |
| `A-PATCH-006` | provenance și evidence sunt byte-closed | source scopes sunt exact pinurile PMORG-Platform/Onyx din BQM; coverage exact bilateral PMORG/EE; raw/classified matches în bijecție; exact/normalized/similarity fixtures detectate; rezoluțiile condiționale trec; 0 recorduri cross-build/surface/mode, unreadable/unscanned/unreviewed/invalid/forbidden/unresolved; 100% evidence refs rezolvă la bytes |
| `A-MIG-001` | instalarea/migrarea din baze curate este repetabilă | 3/3 porniri curate PASS |
| `A-RESTORE-001` | Odoo, Onyx și Semantic Ledger pot fi restaurate independent | 1 restore complet PASS pentru fiecare store per RC |
| `A-SUPPLY-001` | imagini, dependențe și SBOM sunt fixate | 100% imagini prin digest; 0 vulnerabilități Critical/High netriate |

Un risc Critical/High acceptat explicit nu dispare din raport; are owner,
expirare și compensating control. Fără triere, gate-ul este FAIL.

Cele patru celule surface×mode și clasele lor opuse sunt contract-tested numai
cu fixtures/ținte/destinații sintetice. `A-LIC-001` și `A-SURFACE-001` se aplică
separat fiecărui artefact real publicat: un PASS EE nu afirmă existența unei
variante CE, iar CE devine disponibil numai după propriul build real PASS.

Fault cases obligatorii pentru `A-LIC-*`, `A-EVIDENCE-*`, `A-REPORT-*` și
`A-PATCH-*` includ separat: payload DSSE modificat; `payloadType` greșit;
signature goală/necunoscută/revocată; trust policy diferit de pinul baseline;
evidence blob lipsă ori cu hash/size greșit; revocation snapshot expirat;
receipt/evidence pentru alt build, target ori destination; descriptor declarat
sintetic dar derivat client; binding necunoscut/imposibil de măsurat; endpoint,
account, namespace, principal ori redirect schimbat după preflight; admission
reutilizat pentru alt payload; runtime bytes/image diferite de BQM; time receipt
stale, rollback/fork de sequence ori uncertainty peste policy; workload activ
după deadline; measurement/issued/verified future-dated; transfer care
traversează deadline-ul; deployment/distribution scope policy substituit ori
micșorat față de release definition sau cu alt baseline/surface/operație;
build qualification/deviation decision future-dated, expirată ori cu
revalidare restantă; `development_test` către client; role de
qualification lipsă/duplicat/condițional greșit; OCI layer omis; catalog
micșorat cu requirement nemapat; candidat `pass` + patch fără decizie;
record/report/deviation pentru alt build, commit, surface ori mode; no-candidate
din scan complet pe alt tree sau fără search bytes; copie EE sub cale PMORG etichetată
`licensed_patch`; cod PMORG de domeniu sub rădăcină upstream ori patch upstream
în afara seam allowlist-ului; revalidation ratată; ceas indisponibil ori skew
peste policy.
Fiecare caz produce determinist `FAIL` sau `INVALID` înaintea operației.

## 4. G3-B — Odoo, closed world și comenzi

| ID test | Criteriu PASS | Prag |
|---|---|---|
| `B-INSTALL-001` | `pmorg_core` funcționează cu Project-only | 3/3 instalări curate fără HR/Inventory |
| `B-REG-001` | registry-ul corespunde profilului | exact match pentru toate cele 3 profiluri |
| `B-ABSENT-001` | tipurile modulelor absente nu devin canonice | 0 ancore, actions, formalizări sau affordances UI tipizate; textul brut este permis numai ca evidence/external mention etichetat |
| `B-ANCHOR-001` | ancorele rezolvă instanța/compania/recordul corect | 100% din fixture-urile pozitive; 100% refuz pentru cele negative |
| `B-ACL-001` | accesul neautorizat/cross-company este refuzat | 100% refuz înainte de payload/retrieval |
| `B-CLAIM-001` | un singur client obține lease-ul | 0 double claims în 100 curse concurente per profil |
| `B-IDEM-001` | retry-ul nu dublează efectul | 0 efecte duble în 1.000 duplicate commands/events |
| `B-IDEM-002` | aceeași cheie cu request hash diferit este conflict înaintea precondițiilor business | 100% `IDEMPOTENCY_CONFLICT`; zero state/version/event/outbox nou; reordonarea JSON RFC 8785 rămâne replay |
| `B-IDEM-003` | o eroare tehnică retryable reia aceeași comandă, nu îngheață prematur și nu dublează efectul | același command/key/hash ajunge terminal în maximum 4 attempts; exact 1 efect; 0 command nou; la epuizare `RETRY_EXHAUSTED`, `retryable=false`; respingerile non-retryable rămân înghețate |
| `B-IDEM-MIG-001` | fixture-ul inbox v2 respectă request-hash la portare | replay identic; 100% payloaduri diferite refuzate `IDEMPOTENCY_CONFLICT`; 0 rânduri fără payload verificabil importate autoritativ |
| `B-MIG-PROV-001` | fiecare identitate legacy este legată 1:N de targeturi prin manifest și namespace verificabile | exact 1 `LegacySourceIdentity` per tuple și toate binding-urile target așteptate, fără duplicate; SourceArtifact+Evidence și Claim+receipts coexistă; source instance/principal mismatch refuzat; neverificabil = numai `reference-only` |
| `B-APPROVAL-001` | approval-ul este legat necircular de intenția business stabilă | `action_hash` rămâne identic după approval ID, pe run/lease nou și după versiuni pur tehnice; 100% schimbări de payload/`intent_state_hash`/autoritate cer approval nou; execuția recalculează binding-ul și verifică separat versiunea curentă |
| `B-VERSION-001` | write concurent cu versiune veche este refuzat | 100% optimistic conflicts detectate |
| `B-WRITE-001` | nu există comandă generică ORM/SQL | 0 endpointuri/capabilități generice accesibile runtime-ului |
| `B-OUTBOX-001` | efectul și outbox event sunt atomice | 100% cazuri fault-injected reconciliate fără pierdere/duplicare |

## 5. G3-C — Semantic Core

| ID test | Criteriu PASS | Prag |
|---|---|---|
| `C-EVID-001` | duplicatele de transport produc o singură evidence | 0 duplicate ledger rows în 1.000 replay-uri |
| `C-IDEM-001` | retry-ul semantic pe run/correlation nou păstrează operația logică | aceeași key + același semantic body, cu IDs server-set și metadata volatile diferite, întoarce receipt-ul inițial; schimbarea content/source/author/authority produce 100% conflict |
| `C-IDEM-MIG-001` | fixture-ul memory v2 nu transformă `(namespace, external_id)` într-un replay ambiguu | same key/same canonical evidence = un receipt; same key/different content, source ori author = 100% `IDEMPOTENCY_CONFLICT`; 0 silent replay |
| `C-CLAIM-001` | claim fără evidence nu poate fi validat | 100% refuz |
| `C-AUTH-001` | validator greșit/autovalidare este refuzat | 100% refuz în cazurile `must-not` |
| `C-HASH-001` | content hash greșit este refuzat | 100% refuz |
| `C-TEMP-001` | `as_of` distinge valid time și recorded time | 100% expected views pe suita deterministă |
| `C-CONTRA-001` | contradicția este păstrată și blochează efectul cerut | 100% cazuri injectate detectate; 0 claims pierdute |
| `C-SUPER-001` | supersession păstrează istoricul | 100% lanțuri și views curente/istorice corecte |
| `C-RECALL-001` | cazurile deterministe must/must-not sunt corecte | 100% must-retrieve și must-not-retrieve |
| `C-INDEX-001` | indexul poate fi șters și reconstruit | proiecția canonică înainte/după are același hash |
| `C-MCP-001` | MCP este interoperabil și versionat | 100% contract tests cu un client MCP independent |
| `C-TENANT-001` | cross-organization retrieval este refuzat | 0 rezultate/citations în toate cazurile negative |
| `C-HIL-001` | omul/agentul cognitiv nu poate judeca interpretarea claim-ului | 0 verdicturi, approvals, tranziții sau actions/UI/API umane/agentice asupra claim-ului, inclusiv approve/reject integral și editarea kind/owner/termen/predicat/valoare; actorul fiecărei tranziții este serviciul de policy; suprafețele umane pozitive sunt numai vocabulary/anchor reconciliation |
| `C-PRIVACY-001` | denylist/secrets gate refuză înaintea stocării și orchestrării persistente | 0 content, refs, hashes, transcripts, chunks, evidence, prompts ori checkpoint/log/input orchestrator/runner; mesajul nu ajunge la runtime; exact 1 receipt metadata-only |

Scorurile probabilistice ale unui model nu participă la G3-C. Pentru G3-G,
pragurile de extraction/recall se stabilesc pe calibration și se îngheață
înainte de hidden-test.

## 6. G3-D — vertical slice XNX

| ID test | Criteriu PASS | Prag |
|---|---|---|
| `D-XNX-001` | lanțul inițiativă → rezultat este complet | 3/3 runs PASS în `ORG-DIST` |
| `D-TRACE-001` | fiecare efect are actor, autoritate, evidence, comandă și receipt | 100% efecte externe/formale |
| `D-CLOSE-001` | închiderea fără criterii/dovezi/validator este refuzată | 100% cazuri negative |
| `D-EFFECT-001` | taskul operațional este creat o singură dată | exact 1 task și 1 command receipt |
| `D-FORMAL-001` | mutația efectivă de stoc rămâne interzisă în MVP | 0 modificări agentice `stock.move`/quantity |
| `D-TIMELINE-001` | timeline-ul reconstruiește lanțul | 100% evenimente canonice în ordine cauzală |

Scenariul exact și expected outputs sunt în
[scenariul XNX](10-XNX-REFERENCE-SCENARIO.md).

## 7. G3-E — agnosticism organizațional

| ID test | Criteriu PASS | Prag |
|---|---|---|
| `E-BUILD-001` | cele trei profiluri folosesc același build | același commit și aceleași image digests/checksums |
| `E-PROFILE-001` | scenariul comun trece în fiecare profil | 3/3 runs per profil, minimum 9 runs |
| `E-CODE-001` | nu există cod/flag cu numele organizației în core | 0 încălcări în static policy scan |
| `E-ISOLATE-001` | bazele și namespace-urile sunt izolate | 0 cross-profile IDs, evidence, chunks sau receipts |
| `E-MORPH-001` | redenumirea organizației nu schimbă verdictul | 100% metamorphic cases identice semantic |
| `E-MODULE-001` | activarea pack-ului schimbă numai vocabularul permis | exact diff-ul declarat în registry fixture |

Un termen dintr-un modul absent poate apărea citat în evidence, search ori în
UI-ul de guvernanță vocabular/ancoră și poate fi returnat ca
`external_mention`. Nu poate apărea ca tip
canonic, ancoră rezolvată, action, fapt formal sau control UI operațional.

Scenariul comun testează inițiativă, conversație, evidence, claim, task,
outcome și închidere; obiectul de domeniu diferă prin profil.
Fixture-urile normative sunt în
[profilurile organizaționale](13-ORGANIZATION-PROFILES.md).

## 8. G3-F — longitudinalitate și recovery

| ID test | Criteriu PASS | Prag |
|---|---|---|
| `F-SILENCE-001` | follow-up și escaladare apar la tick-ul corect | abatere 0 ticks față de politica fixture-ului |
| `F-DUE-001` | răspunsul/approval-ul corelat și tick-ul scadent reactivează taskul înainte de claim | 100% `waiting_response\|waiting_approval\|scheduled → ready` exact o dată; claim nou posibil; 0 activări premature |
| `F-RESTART-001` | restartul Onyx/runner nu pierde obligația | 0 obligații pierdute în 3/3 runs per restart point |
| `F-LEASE-001` | lease-ul expirat este recuperat sigur | 100% recuperări; 0 rezultate tardive acceptate automat |
| `F-LATE-001` | răspunsul întârziat se corelează corect | 100% la conversația/taskul așteptat |
| `F-DUP-001` | replay-ul longitudinal nu dublează efecte | 0 duplicate tasks/messages/effects |
| `F-ODOO-001` | Odoo indisponibil blochează live validation și writes | 100% refuz/pending; 0 efecte pe snapshot pretins curent |
| `F-MEM-001` | Semantic Core indisponibil produce `memory_pending` și recovery | 100% reluări fără pierdere/duplicare |
| `F-CONFLICT-001` | schimbarea manuală Odoo este reconciliată | 100% conflicte detectate; 0 overwrite tăcut |
| `F-PLAN-001` | contradicția/supersession produce replanificare versionată | 100% scenarii; versiunea veche rămâne în istoric |
| `F-GAP-001` | D1 detectează efectul material fără proveniență și închide bucla prin evidence nouă | 100% cazuri must detectate, 0 duplicate gaps, coverage rate exactă oracle-ului |
| `F-MIG-STATE-001` | fixture-ul v2 mapează task/run fără lease viu ori verdict inventat | expected exact pentru done/failed/needs_review/released/waits/approval/blocked/expired și effect classes; toate cazurile incomplete intră `review`/`reference-only` |
| `F-MIG-LONG-001` | follow-up/escalation legacy devin evenimente, nu contoare copiate | contoare/niveluri recalculate exact din receipts; versiune v3 monotonă nouă; 0 evenimente sintetizate din valori agregate legacy |
| `F-CLOSE-001` | stack restart complet permite închiderea corectă | 3/3 runs longitudinale combinate PASS |

## 9. Controale globale de evaluare

| ID test | Criteriu PASS | Prag |
|---|---|---|
| `X-PROD-001` | manifestul nu conține endpoint/credential de producție | 0 potriviri și probe de conectivitate blocate |
| `X-ORACLE-001` | SUT nu poate accesa oracle/scorer | 100% probe/canaries blocate; 0 disclosure |
| `X-TRACE-001` | trasa este completă și sigilată | 100% evenimente obligatorii; hash chain valid |
| `X-SECRET-001` | secretele nu apar în artefacte | 0 secrete confirmate după scan/redaction test |
| `X-EGRESS-001` | SUT nu emite telemetrie/update traffic și nu ocolește proxy-ul permis | 0 conexiuni/DNS neașteptate; 100% negative reachability blocate; excepțiile corespund manifestului |
| `X-RESET-001` | resetul distruge volumele și rotește credențialele | 100% pentru fiecare run calificat |

Un eșec `X-PROD`, `X-ORACLE` sau `X-TRACE` face runul `INVALID` și blochează
release-ul până la remedierea harness-ului. O tentativă nepermisă inițiată de
SUT rămâne simultan defect de produs și nu este ștearsă de verdictul INVALID.

## 10. Performanță și cost

`RB-1/C2` cere măsurarea, nu inventează un SLO independent de hardware:

- latență P50/P95/P99 pe Turn API, Odoo command și Semantic recall;
- throughput, backlog, outbox lag și index lag;
- CPU/RAM/storage per profil;
- cost per cognitive step la G3-G;
- durată restore și rebuild index.

Primul RC produce baseline-ul pe un profil hardware versionat. SLO-urile de
producție se stabilesc prin ADR după măsurare; lipsa raportării este FAIL, dar
o valoare nu este declarată arbitrar defect funcțional în MVP.

## 11. Matrice cerință → suită → artefact

| Cerințe | Suite | Artefact principal |
|---|---|---|
| `PR-001..012` | `D-XNX-*`, `F-*` | `scenario-report.json`, initiative timeline |
| `ODO-001..009` | `B-*`, `D-FORMAL-*` | registry snapshot, Odoo audit export |
| `MEM-001..012` | `C-*`, `F-MEM-*`, `F-GAP-*` | semantic projection, validation/timeline și coverage report |
| `INT-001..006` | `C-PRIVACY-*`, `D-TRACE-*`, channel contract tests | privacy receipt și message/evidence/receipt chain |
| `ORC-001..006` | runner contracts, `F-*` | run/task event trace |
| `PLT-001` | `A-FORK-001`, `A-UPSTREAM-001`, `A-LIC-001`, `A-SURFACE-001` | upstream/spec pins, version endpoint, surface claim și fork qualification |
| `PLT-002` | `A-MIG-001`, `A-RESTORE-001`, `C-INDEX-001`, `C-MCP-001` | Semantic Core schema/migrations, independent store și API contract |
| `PLT-003` | `A-RESTORE-001`, `E-ISOLATE-001` | DB/role manifests, negative cross-store probes și restore reports |
| `PLT-004` | `A-PATCH-001` | ownership-boundary scan, seam allowlist, exact upstream diff și patch-ledger report |
| `PLT-005` | `A-LIC-001`, `A-REPRO-001`, `A-EVIDENCE-001`, `A-REPORT-001` | artifact set, build payload/DSSE, qualification/evidence bundle și rapoarte complete |
| `PLT-006` | `A-PATCH-002..006` | capability catalog/search/disposition și provenance/evidence reports |
| `PLT-007` | `A-LIC-002` | per-target measurement și deployment admission |
| `PLT-008` | `A-LIC-003` | per-destination distribution admission |
| `SEC-001..006` | `B-ACL-*`, `C-TENANT-*`, `X-*` | security scorecard și negative traces |
| `EVAL-001..007` | G3-A–G3-F | signed run bundle și verdict |

## 12. Artefactele obligatorii ale unui release candidate

```text
baseline-manifest.json
expected-artifact-catalog.json
artifact-set.json
image-lock.json

qualification/build-qualification-manifest.json
qualification/release-build-definition.payload.json
qualification/release-build-definition.dsse.json
qualification/build-recipe.json
qualification/build-input-set.json
qualification/runtime-scope-policy-map.json
qualification/build-qualification-attestation.payload.json
qualification/build-qualification-attestation.dsse.json
qualification/qualification-bundle-index.json
qualification/qualification-policy-map.json
qualification/surface-mode-report.json
qualification/capability-catalog.json
qualification/capability-disposition-report.json
qualification/capability-evidence-bundle-index.json
qualification/capability-scope-rule.json
qualification/applicable-requirement-set.json
qualification/capability-disposition-records/**
qualification/candidate-search/**
qualification/candidate-qualification/**
qualification/post-disposition-qualification/**
qualification/capability-deviation-decisions/**
qualification/provenance-scan-report.json
qualification/provenance-evidence-bundle-index.json
qualification/provenance-source-scopes/**
qualification/provenance-path-inventory.json
qualification/provenance-raw-matches.json
qualification/provenance-match-records.json
qualification/ee-inventory-report.json | qualification/ce-boundary-report.json
qualification/sbom-index.json
qualification/sbom/**
qualification/license-report.json
qualification/patch-ledger-report.json
qualification/vulnerability-report.json
qualification/upstream-test-report.json

evidence/indexes/*.json
evidence/trust-policy/**
evidence/certificates/**
evidence/revocation/**
evidence/trusted-time/**
evidence/verifier-receipts/**
evidence/resources/**
evidence/authorizations/**
evidence/provenance/**

deployments/*/*/deployment-payload-descriptor.json
deployments/*/*/target-descriptor.json
deployments/*/*/target-measurement-attestation.payload.json
deployments/*/*/target-measurement-attestation.dsse.json
deployments/*/*/deployment-admission.payload.json
deployments/*/*/deployment-admission.dsse.json
deployments/*/*/use-receipts/*.payload.json
deployments/*/*/use-receipts/*.dsse.json

distributions/*/*/distribution-payload-descriptor.json
distributions/*/*/release-metadata-bundle-index.json
distributions/*/*/destination-descriptor.json
distributions/*/*/destination-measurement-attestation.payload.json
distributions/*/*/destination-measurement-attestation.dsse.json
distributions/*/*/distribution-admission.payload.json
distributions/*/*/distribution-admission.dsse.json
distributions/*/*/use-receipts/*.payload.json
distributions/*/*/use-receipts/*.dsse.json

migration-and-restore-report.json
profiles/*/registry-snapshot.json
profiles/*/world.lock
runs/*/public-manifest.json
runs/*/sealed-event-trace.jsonl
runs/*/canonical-odoo-projection.json
runs/*/canonical-semantic-projection.json
runs/*/scorecard.json
runs/*/verdict.json
```

Artefactele de authorization, metadata comercială, resource evidence,
deployment/distribution descriptors și receipts sunt `sealed_private`.
Manifestele publice conțin numai refs content-addressed, verdicturi și coduri
de refuz metadata-only. Fără artefactele de mai sus sau dacă orice hash referit
de BQM, DSSE payload, admission ori scorecard nu rezolvă la bytes în bundle,
afirmația de PASS nu este reproductibilă și gate-ul este `INVALID`.
