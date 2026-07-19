# PMORG v3 — requirements baseline

| Câmp | Valoare |
|---|---|
| Status | Accepted, cu corrigendum implementabil |
| Baseline | `RB-1/C2` |
| Versiune produs | `3.0-baseline.3` |
| Data acceptării | 2026-07-19 |
| Scope | MVP structural și longitudinal, G3-A–G3-F |

## 1. Scopul baseline-ului

Acest document îngheață cerința PMORG v3 suficient pentru proiectare tehnică,
estimare și implementare fără reinterpretarea intenției produsului.

Baseline-ul nu fixează încă tagul Onyx, revizia Odoo, providerul LLM sau
implementarea orchestratorului persistent. Acestea sunt selecții de implementare/calificare care se
înregistrează ulterior în manifest, fără să schimbe cerința.

## 2. Ierarhia normativă

În caz de contradicție, ordinea este:

1. acest requirements baseline și ADR-urile `Accepted`;
2. [contractele v1](09-CONTRACTS.md),
   [state machines și politicile](11-STATE-MACHINES-POLICIES.md) și
   [criteriile de acceptare](12-ACCEPTANCE-TRACEABILITY.md);
3. [scenariul canonic XNX](10-XNX-REFERENCE-SCENARIO.md);
4. [profilurile organizaționale](13-ORGANIZATION-PROFILES.md);
5. definiția produsului, arhitectura și modelul de domeniu v3;
6. documentele v2 și implementările v1/SB2/SB3, exclusiv ca referință.

O schimbare de fond după `RB-1/C2` cere ADR nou, impact asupra cerințelor/testelor
și versiune nouă a baseline-ului.

## 3. Cerința principală

> PMORG v3 SHALL funcționa ca operator organizațional persistent Odoo-first:
> primește sau identifică o inițiativă, clarifică scopul cu persoanele
> relevante, creează și urmărește planul și taskurile, intervine și
> escaladează în timp, adaptează planul, verifică rezultatul și păstrează o
> memorie organizațională validată, ancorată și temporală.

`SHALL` indică cerință obligatorie. `SHOULD` indică recomandare care poate fi
încălcată numai prin decizie documentată. `MAY` indică opțiune.

## 4. Cerințe funcționale de produs

| ID | Cerință obligatorie |
|---|---|
| `PR-001` | PMORG SHALL accepta o inițiativă explicită și SHALL putea crea una dintr-un semnal permis de politică. |
| `PR-002` | Fiecare inițiativă SHALL avea owner, obiectiv, criterii de succes, stare și versiune. |
| `PR-003` | PMORG SHALL identifica participanții necesari și SHALL purta conversații corelate cu inițiativa și taskul. |
| `PR-004` | PMORG SHALL produce un plan versionat și taskuri cu responsabili, termene, dependențe și rezultat așteptat. |
| `PR-005` | Responsabilitățile și angajamentele SHALL necesita confirmarea prevăzută de politică. |
| `PR-006` | Fiecare inițiativă activă SHALL avea `next_check_at` sau o stare explicită `blocked`, `paused` ori `degraded`. |
| `PR-007` | PMORG SHALL detecta determinist termene, tăcere, lipsă progres, dependențe blocate și lease-uri expirate. |
| `PR-008` | PMORG SHALL putea iniția follow-up, clarificare și escaladare în limitele politicii de autonomie. |
| `PR-009` | PMORG SHALL păstra versiuni de plan și SHALL explica replanificarea. |
| `PR-010` | O inițiativă SHALL putea fi închisă numai după criterii, dovezi și verificarea/autoritatea cerută. |
| `PR-011` | Starea și următoarea acțiune SHALL supraviețui restartului Onyx-PMORG și orchestratorului. |
| `PR-012` | Un runtime nou SHALL putea continua inițiativa fără sesiunea LLM anterioară. |

## 5. Cerințe Odoo-first

| ID | Cerință obligatorie |
|---|---|
| `ODO-001` | Odoo SHALL fi sursa stării business formale curente și a efectelor operaționale. |
| `ODO-002` | `project.task` extins SHALL fi registrul canonic al muncii organizaționale. |
| `ODO-003` | PMORG SHALL folosi `pmorg.identity` pentru owneri, participanți, validatori, agenți și sisteme. |
| `ODO-004` | Odoo SHALL publica un capability registry versionat din module, anchor packs, companie, ACL și politici. |
| `ODO-005` | Un modul sau tip absent din registry SHALL fi absent din ancore, actions și formalizări. |
| `ODO-006` | O ancoră SHALL include instanță, companie, tip, model, record, registry/fingerprint și versiunea observată. |
| `ODO-007` | Orice efect SHALL folosi o comandă business îngustă, autorizată, idempotentă și auditată. |
| `ODO-008` | Onyx, orchestratorul și modelele SHALL NOT primi acces ORM, SQL sau credential de DB Odoo generic. |
| `ODO-009` | Odoo SHALL rămâne operabil manual când runtime-ul cognitiv sau orchestratorul este indisponibil. |

## 6. Cerințe de memorie

| ID | Cerință obligatorie |
|---|---|
| `MEM-001` | Evidence și Claim SHALL fi obiecte distincte; un claim validat SHALL avea evidence. |
| `MEM-002` | Evidence SHALL păstra sursa, autorul structural, content hash, scope-ul și timpii relevanți. |
| `MEM-003` | Validarea SHALL evalua integritatea, identitatea, proveniența, ancora, registry-ul, accesul, autoritatea, timpul și contradicțiile. |
| `MEM-004` | Autovalidarea SHALL fi refuzată când politica cere validare independentă. |
| `MEM-005` | Contradiction și Supersession SHALL fi relații persistente și SHALL NOT șterge istoricul. |
| `MEM-006` | Semantic Core SHALL separa `occurred_at`, `captured_at`, `recorded_at` și `valid_from/to`. |
| `MEM-007` | Recall SHALL filtra determinist organizația, compania, ACL, registry-ul, timpul și statusul înainte de răspuns. |
| `MEM-008` | Scorul vectorial SHALL NOT acorda acces, autoritate ori status de adevăr. |
| `MEM-009` | Semantic Ledger SHALL supraviețui ștergerii și reconstruirii indexului Onyx/search. |
| `MEM-010` | Semantic Core SHALL expune același model semantic prin API intern și MCP extern standard/versionat. |
| `MEM-011` | Interpretarea claim-urilor SHALL fi automată; oamenii și agentul cognitiv SHALL NOT emite verdict, approval ori tranziție de claim. HIL semantic SHALL fi limitat la entități/tipuri noi și matching de ancoră ambiguu cu consecință; aprobările efectelor și verificarea outcomes business rămân fluxuri distincte. |
| `MEM-012` | Controllerul determinist din addon/control-plane-ul PMORG Odoo SHALL detecta gaps de proveniență pentru efectele materiale folosind receipts Semantic Core, SHALL păstra lifecycle-ul lor în Odoo și SHALL raporta rata de acoperire fără verdict despre persoane. |

## 7. Cerințe de interacțiune și orchestrare

| ID | Cerință obligatorie |
|---|---|
| `INT-001` | Fiecare turn oficial SHALL trece prin Turn Coordinator. |
| `INT-002` | UI-ul PMORG și Gateway SHALL intra mai întâi în Turn Admission; orchestratorul/runnerul SHALL primi numai `AdmittedMessage`, apoi SHALL continua în același Turn API și aceeași politică. |
| `INT-003` | Identitatea expeditorului SHALL proveni structural din binding; SHALL NOT fi ghicită din text. |
| `INT-004` | Orice mesaj admis de `INT-006` SHALL fi capturat durabil ca evidence înainte de execuția cognitivă care îl interpretează. |
| `INT-005` | Fiecare action SHALL avea preflight determinist și receipt. |
| `INT-006` | Fiecare mesaj SHALL trece prin privacy/secrets gate după identity binding și înainte de orice transcript, evidence, index, prompt sau checkpoint/log orchestrator; refuzul SHALL persista numai metadata minimă fără conținut, referință ori hash și SHALL NOT ajunge la orchestrator/runner/runtime. |
| `ORC-001` | Un orchestrator persistent implementation-agnostic SHALL conduce procesele longitudinale; starea longitudinală canonică SHALL rămâne în Odoo, iar checkpointurile orchestratorului SHALL fi numai metadata de execuție; runnerul determinist SHALL demonstra același contract în MVP, iar Hermes MAY fi un adaptor calificat. |
| `ORC-002` | Orchestratorul SHALL apela `execute_cognitive_step`; SHALL NOT folosi chat generic drept contract longitudinal. |
| `ORC-003` | O execuție cognitivă SHALL fi bounded, versionată și idempotentă. |
| `ORC-004` | Scheduling, retry și checkpoint ale orchestratorului SHALL NOT deveni starea business canonică. |
| `ORC-005` | Controller-ele SHALL executa cel mult un pas idempotent și SHALL persista următoarea verificare. |
| `ORC-006` | Un controller system-only SHALL reactiva idempotent munca `waiting_response`, `waiting_approval` sau `scheduled` pe eveniment corelat ori timp trusted scadent înainte de un claim nou. |

## 8. Cerințe de platformă și securitate

| ID | Cerință obligatorie |
|---|---|
| `PLT-001` | PMORG v3 SHALL fi construit ca fork guvernat al Onyx, cu baseline tag + SHA exact și `onyx_surface` plus `usage_mode` declarate. |
| `PLT-002` | Semantic Core SHALL fi bounded context first-class, cu ownership și migrații proprii. |
| `PLT-003` | Odoo DB, Onyx DB și Semantic Ledger SHALL folosi baze și roluri distincte; Odoo SHALL NOT scana DB-urile PMORG. |
| `PLT-004` | Codul PMORG de domeniu SHALL fi separat de codul upstream, iar patchurile upstream SHALL fi inventariate. |
| `PLT-005` | Fiecare build SHALL fixa `onyx_surface: ce|ee` și `usage_mode: development_test|production` într-un manifest și o atestare semnată, detașate de setul exact de artefacte calificat. Două builduri curate independente SHALL produce același artifact-set hash și același qualification payload hash. `ce` SHALL exclude EE; orice `ee` SHALL avea inventar complet. |
| `PLT-006` | O capabilitate Onyx existentă SHALL fi reutilizată implicit dacă trece contractele PMORG, izolarea, securitatea și constrângerile comerciale. Catalogul, candidate refs structurate, recordurile condiționale, report envelope și provenance scan versionat SHALL demonstra exact-once `reuse|patch|pmorg_independent`, implementation/patch refs, verdict post-disposition, evidence și ADR/waiver. Codul EE SHALL NOT fi copiat în module PMORG, iar fiecare patch direct EE SHALL declara `license_class=onyx-enterprise` fără ownership PMORG. |
| `PLT-007` | Orice deploy și startup SHALL recomputa descriptorul/fingerprint-ul canonic al țintei și SHALL valida measurement attestation plus un `DeploymentAdmissionRecord` content-addressed, semnat, nerevocat și legat de artifact set, build attestation, target, suprafață, mod și timp trusted. Orice `development_test`, CE sau EE, SHALL admite numai sandbox sintetic; `ce + production` SHALL cere release admission, iar `ee + production` SHALL cere suplimentar autorizare Enterprise. Unknown/unmeasurable, missing, expired, revoked, mismatch sau verifier neacceptat SHALL refuza fail-closed. |
| `PLT-008` | Orice registry publish ori artifact export SHALL valida un `DistributionAdmissionRecord`. Orice `development_test`, CE sau EE, SHALL permite numai o destinație sintetică controlată; `production` SHALL urma aceeași separare CE/EE și aceeași autorizare aplicabilă ca deploymentul. |
| `SEC-001` | Fiecare operație SHALL avea `organization_id`, instanță Odoo, companie, identitate și registry fingerprint. |
| `SEC-002` | Accesul cross-organization și cross-company SHALL fi refuzat înainte de retrieval sau action. |
| `SEC-003` | Secretele SHALL NOT apărea în evidence, prompturi, logs ori receipts. |
| `SEC-004` | Prompt injection SHALL NOT activa un tool, anchor type sau nivel de autonomie nepermis. |
| `SEC-005` | Memoria personală Onyx SHALL fi dezactivată pentru agenții PMORG în MVP. |
| `SEC-006` | Telemetria și update checks upstream SHALL fi dezactivate; SUT SHALL avea egress deny-by-default, cu excepții allow-listed și auditate numai în gate-urile care le cer. |

## 9. Cerințe de evaluare

| ID | Cerință obligatorie |
|---|---|
| `EVAL-001` | Niciun test, benchmark, calificare sau pilot SHALL rula în producție. |
| `EVAL-002` | MVP-ul SHALL folosi exclusiv date, identități, canale și credențiale sintetice/dedicate. |
| `EVAL-003` | Oracle-ul, gold labels și scorerul SHALL fi inaccesibile SUT. |
| `EVAL-004` | Același build SHALL trece profilurile minimal, servicii și distribuție fără cod per organizație. |
| `EVAL-005` | MVP-ul SHALL include scenariu longitudinal cu timp virtual, restart, duplicate, contradicție și supersession. |
| `EVAL-006` | Fiecare verdict SHALL fi legat de run bundle, sealed trace și checksum-uri. |
| `EVAL-007` | Un caz structural `must` eșuat SHALL produce FAIL indiferent de scorul agregat. |

## 10. Scope-ul înghețat al MVP-ului

MVP-ul include:

- fork Onyx-PMORG real;
- addon-uri Odoo PMORG reale;
- Semantic Core real și MCP interoperabil;
- runner determinist, canal simulat și ceas virtual;
- trei profiluri organizaționale;
- vertical slice XNX și scenariile longitudinale;
- G3-A–G3-F din [MVP](04-MVP.md).

MVP-ul exclude:

- un orchestrator persistent real (Hermes rămâne opțiune);
- model stochastic drept condiție de PASS;
- canal real;
- date reale;
- multi-tenant la scară;
- fine-tuning, pilot și producție.

Aceste excluderi nu elimină responsabilitățile produsului. Ele amână numai
implementarea concretă la G3-G, G3-H sau G3-I.

## 11. Deciziile înghețate în `RB-1/C2`

ADR-309–316 sunt acceptate cu următoarea interpretare:

- Turn Coordinator este obligatoriu;
- bazele și rolurile autoritare sunt separate;
- `PMORG` și `PMORG-Platform` sunt repository-uri distincte;
- Onyx-PMORG este workspace-ul principal, Odoo rămâne formal/fallback;
- suprafața Onyx și modul de utilizare sunt independente; `ce` nu este
  critical path pentru Semantic Core ori contracte; orice `ee` cere inventar
  complet; ambele `development_test` admit numai sandbox/destinație sintetică;
  `ce + production` cere release admission, iar `ee + production` cere
  suplimentar autorizare Enterprise fail-closed;
- longitudinalitatea deterministă este parte din MVP, nu etapă opțională.
- HIL asupra semanticii este exclusiv vocabular/ancoră; claim-urile nu au
  coadă umană de interpretare, iar approvals/outcomes business rămân fluxuri
  de autoritate distincte;
- detectorul golului este componentă v3, cu stare Odoo și digest Onyx-PMORG;
- `pmorg-contracts/1.0` supersedează pentru v3 wire contractele v2 conform
  [mapării normative](14-V2-CONTRACT-SUPERSESSION.md).

## 12. Variabile rămase, fără ambiguitate de cerință

Următoarele se decid în bootstrap și se fixează în manifest:

- tagul/SHA Onyx calificat;
- commitul și digestul Odoo;
- versiunea PostgreSQL/search/object store;
- numele finale ale pachetelor și tabelelor;
- catalogul capabilităților Onyx/PMORG, trust root-ul și politica verifier-ului
  pentru build/deployment admission;
- modelul/providerul pentru G3-G;
- implementarea exactă a adaptorului de orchestrator pentru G3-H (Hermes opțional);
- primul canal real pentru G3-I.

Niciuna nu poate modifica ownership-ul, closed world-ul, contractele de
business sau gate-urile fără ADR și baseline nou.

## 13. Readiness pentru implementare

`RB-1/C2` este requirements-ready: cerințele, semantica schemelor, scenariile,
tranzițiile și pragurile sunt definite în această suită. Nu mai există o
decizie de produs deschisă care să blocheze G3-A–G3-F.

Prima etapă de implementare materializează, fără reinterpretare:

1. contractele din `09-CONTRACTS.md` ca JSON Schema și contract tests;
2. adaptorul de portare și testele de supersession din
   `14-V2-CONTRACT-SUPERSESSION.md`, fără a-l expune ca API v3;
3. XNX și celelalte profiluri ca YAML public, oracle privat și `world.lock`;
4. state machines/politicile ca tabele executabile și teste de tranziție;
5. criteriile G3-A–G3-F ca probe automate și artefacte de verdict;
6. repository-ul `PMORG-Platform` dintr-un Onyx upstream curat și fixat.

Acestea sunt livrabile de implementare, nu clarificări suplimentare ale
cerinței.
