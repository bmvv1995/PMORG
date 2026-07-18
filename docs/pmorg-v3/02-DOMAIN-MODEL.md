# PMORG v3 — modelul de domeniu și Semantic Core

| Câmp | Valoare |
|---|---|
| Status | Accepted — requirements baseline `RB-1` |
| Versiune | `3.0-baseline.1` |
| Data | 2026-07-18 |

## 1. Rolul Semantic Core

Semantic Core este mecanismul prin care PMORG poate învăța în timp fără să
confunde conversația, căutarea sau outputul unui model cu adevărul
organizațional.

El are patru responsabilități:

1. capturează evidența cu identitate și proveniență;
2. reprezintă claims și relațiile dintre ele;
3. aplică validarea de autoritate, ancoră, timp și contradicție;
4. produce recall și timeline explicabile, în scope-ul permis.

Semantic Core nu este:

- un vector store;
- istoricul brut de chat;
- un knowledge graph care copiază toate modelele Odoo;
- sursa stării business curente;
- un sistem în care scorul de similitudine decide adevărul.

## 2. Agregatele produsului

### 2.1 În Odoo

| Agregat | Responsabilitate |
|---|---|
| `Organization` / `Company` | scope business și separare de date |
| `pmorg.identity` | persoană, agent sau sistem și legăturile sale autorizate |
| `pmorg.initiative` | unitatea longitudinală de la intenție la rezultat |
| `pmorg.objective` | obiectivul și constrângerile explicite |
| `pmorg.success.criterion` | condiția verificabilă de închidere |
| `pmorg.plan.version` | plan versionat și aprobări |
| `project.task` extins | munca umană, agentică, hibridă sau de monitorizare |
| `pmorg.commitment` | angajament formal și confirmat |
| `pmorg.intervention` / `escalation` | urmărire și escaladare formală |
| `pmorg.outcome` | rezultat și verdict de verificare |
| `pmorg.monitoring.policy` | termene, tăcere, follow-up și escaladare |
| `pmorg.autonomy.policy` | nivelul permis pentru fiecare clasă de acțiune |
| `pmorg.capability.registry` | universul de ancore și acțiuni publicat |
| outbox, inbox, task run și events | execuție sigură și auditabilă |

### 2.2 În Semantic Core

| Tip | Rol |
|---|---|
| `OrganizationContext` | scope-ul obligatoriu al operației |
| `RegistrySnapshot` | copia imuabilă a vocabularului negociat |
| `AnchorReference` | legătura versionată către o entitate Odoo |
| `SourceArtifact` | mesaj, document, fișier ori observație identificabilă |
| `Evidence` | porțiune relevantă din sursă, cu hash și autor |
| `Claim` | propoziție structurată susținută de evidență |
| `ClaimAssessment` | rezultat al unei probe sau reguli de validare |
| `ValidationDecision` | verdict autorizat, cu politică și motiv |
| `Contradiction` | relație explicită între claims incompatibile |
| `Supersession` | relație prin care un claim îl înlocuiește temporal pe altul |
| `CommitmentMemory` | promisiunea observată și legătura spre formalizarea Odoo |
| `DecisionMemory` | decizie observată, autoritate și scope |
| `OutcomeEvidence` | dovada folosită la verificarea rezultatului |
| `Receipt` | efect, livrare sau formalizare confirmată extern |
| `ConversationBinding` | legătura conversație–inițiativă–task–participanți |
| `TaskBinding` | legătura dintre elementul semantic și munca formală |

`AuthorityGrant` poate fi proiectat în Semantic Core pentru evaluare istorică,
dar autoritatea operațională canonică rămâne în Odoo. Ledgerul păstrează
snapshotul sau referința verificată la momentul deciziei.

## 3. Evidence și Claim sunt obiecte diferite

`Evidence` descrie ce a fost efectiv observat:

```text
id · organization_context · source_artifact_id · content_ref · content_hash
author_identity · captured_at · declared_occurred_at · channel metadata
initiative/task/conversation bindings · access_scope
```

`Claim` descrie ce se afirmă pe baza uneia sau mai multor evidențe:

```text
id · subject_anchor(s) · predicate · normalized_value
claim_kind · evidence_refs · proposer · confidence_metadata
valid_from · valid_to · status · policy_version
```

Reguli:

- aceeași evidență poate susține mai multe claims;
- același claim poate avea mai multe evidențe independente;
- un claim fără evidență nu poate deveni validat;
- textul generat de AI este o propunere sau evidență despre outputul AI, nu
  dovadă a realității afirmate;
- duplicatele de transport nu creează evidence duplicată;
- deduplicarea evidence și deduplicarea claims sunt procese diferite.

## 4. Stările unui claim

```text
proposed
  → under_review
  → validated
  → disputed
  → superseded
  → expired

proposed / under_review
  → rejected
```

Un claim `validated` poate deveni `disputed` când apare o contradicție și
`superseded` când o afirmație mai nouă îl înlocuiește pentru un interval.
Nicio tranziție nu șterge evidence ori verdictul anterior.

`fact`, `decision`, `commitment`, `preference`, `observation`, `hypothesis`
și `external_mention` sunt tipuri semantice, nu înlocuitori pentru statusul
de validare.

## 5. Validarea

Validarea este un set de assessments explicite, nu un singur scor:

| Dimensiune | Întrebare |
|---|---|
| integritate | sursa și conținutul corespund hash-ului capturat? |
| identitate | autorul este legat structural de o identitate PMORG? |
| proveniență | putem reconstrui sursa și lanțul de procesare? |
| ancorare | ancora există live, în instanța și compania corectă? |
| registry | tipul este publicat de snapshotul negociat? |
| acces | actorul și validatorul puteau vedea/folosi entitatea? |
| autoritate | autorul/validatorul avea autoritatea necesară la acel moment? |
| timp | claim-ul are un interval de valabilitate coerent? |
| consistență | există contradicții active ori dovezi incompatibile? |
| independență | politica cere un validator sau o dovadă distinctă de autor? |
| formalizare | efectul Odoo necesar există și are receipt? |

Citirea live din Odoo este o probă importantă, nu un shortcut universal.
Faptul că un record curent pare compatibil nu înlocuiește proveniența,
autoritatea și timpul.

Autovalidarea este refuzată implicit când politica cere validare
independentă. Modelul poate recomanda un verdict, dar nu își acordă singur
autoritate.

## 6. Timpul

Semantic Core păstrează separat:

```text
occurred_at       # când sursa spune că s-a întâmplat
captured_at       # când PMORG a primit evidența
recorded_at       # când ledgerul a persistat obiectul
valid_from/to     # intervalul pentru care claim-ul este valabil
superseded_at     # când a fost înlocuit
```

În sandbox, timpul de business vine dintr-un `tick_id` emis de ceasul trusted.
Clientul nu poate trimite un `now` autoritativ. În producție, timpul
autoritativ este rezolvat server-side.

Query-urile `as_of` trebuie să poată răspunde atât „ce credeam la momentul
X?”, cât și „ce știm acum că era valabil la momentul X?”. Acestea sunt
întrebări diferite.

## 7. Contradicție și supersession

O contradicție este o relație first-class:

```text
claim_a · claim_b · contradiction_kind · detected_by
detected_at · evidence_refs · resolution_status · resolution_ref
```

Sistemul păstrează ambele claims și marchează efectul asupra recall-ului.
Un conflict nerezolvat nu este ascuns prin alegerea textului cu scor vectorial
mai mare.

Supersession afirmă că un claim nou îl înlocuiește pe altul într-un scope și
interval definite. El nu declară automat că vechiul claim a fost fals la
momentul lui.

## 8. Closed world și vocabular

Există trei niveluri de vocabular:

1. **vocabular de sursă** — liber, păstrat în evidence;
2. **vocabular canonic business** — anchor types și relații publicate de
   Odoo/anchor packs;
3. **vocabular operațional** — comenzile permise de registry și politici.

Un termen necunoscut poate fi:

- text brut;
- `external_mention`;
- alias candidat;
- întrebare de clarificare.

Nu poate deveni automat tip de ancoră, relație canonică sau comandă. Aliasurile
și pack-urile noi trec prin review, versionare și publicare explicită.

## 9. Recall

Recall-ul este o conductă controlată:

```text
query + OrganizationContext
  → candidate retrieval din Onyx/search și ledger
  → filtrare strictă pe tenant, ACL, registry și timp
  → rezoluție live a ancorelor necesare
  → aplicare contradiction/supersession/validation status
  → MemoryView explicabil
```

`MemoryView` include pentru fiecare rezultat:

```text
claim/evidence ID · status · source/provenance · anchors
valid time · recorded time · contradiction/supersession links
live-state label · access scope · motivul includerii
```

Retrievalul vectorial propune candidați. Nu acordă acces, nu validează și nu
decide adevărul.

## 10. Turn Coordinator

Orice mesaj oficial — din UI sau gateway — trece determinist prin:

```text
1. validare OrganizationContext și identity binding
2. capturare durabilă SourceArtifact + Evidence
3. recall autorizat
4. execuție cognitivă Onyx
5. preflight pentru fiecare action/tool
6. capturare claim/command proposals
7. validare semantică și comandă Odoo controlată
8. persistarea receipts și a răspunsului
```

Endpointul generic de chat care ar ocoli acest pipeline este dezactivat sau
inaccesibil în distribuția PMORG. Pașii 1, 2, 5, 6 și 7 nu sunt tool-uri pe
care modelul alege dacă să le apeleze.

## 11. Izolarea organizațională

Toate cheile și indexurile semantice sunt scoped prin `organization_id` și
`odoo_instance_uuid`; unde este relevant, și prin `company_id`.

Testele obligatorii includ:

- acces cross-organization și cross-company refuzat;
- același `res_id` în două instanțe Odoo nu produce coliziune;
- registry snapshot diferit nu reutilizează o ancoră incompatibilă;
- ștergerea indexului Onyx nu șterge ledgerul;
- reconstruirea indexului nu schimbă statusurile semantice;
- exportul și ștergerea respectă scope-ul și politica de retenție.

## 12. Suprafața minimă de domeniu

API-ul intern și MCP extern trebuie să păstreze aceeași semantică:

```text
negotiate_registry(context, descriptor)
capture_evidence(context, source, author, content_ref)
propose_claim(context, evidence_refs, normalized_claim)
assess_claim(context, claim_id, assessment)
validate_claim(context, claim_id, authority_ref, policy_version)
record_contradiction(context, claim_ids, evidence_refs)
supersede_claim(context, old_id, new_id, scope)
record_commitment(context, claim_id, odoo_binding)
record_outcome(context, evidence_refs, odoo_binding)
recall(context, query, temporal_scope)
get_timeline(context, anchors, temporal_scope)
```

Contractele exacte se îngheață înaintea implementării adaptorului Hermes.
