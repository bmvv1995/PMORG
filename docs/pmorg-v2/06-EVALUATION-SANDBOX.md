# PMORG — sandboxul complet de evaluare

| Câmp | Valoare |
|---|---|
| Status | Propunere canonică pentru revizuire |
| Versiune | 0.1 |
| Data | 2026-07-17 |
| Domeniu | Arhitectura, izolarea, datele și verdictul mediului de evaluare |
| Relație | concretizează [MVP-ul](02-MVP.md) și [strategia de date a memoriei](05-MEMORY-DATA.md) |
| Implementare curentă | Un substrat remote existent acoperă numai parțial S0; nu este sandboxul complet descris aici |

## 1. Întrebarea la care răspunde

Sandboxul trebuie să permită un răspuns verificabil la întrebarea:

> Poate același produs PMORG să conducă longitudinal o inițiativă până la un
> rezultat verificat, în organizații Odoo diferite, folosind numai informația
> pe care ar fi putut-o afla legitim, fără acces la răspunsurile evaluatorului?

Nu este suficient ca o demonstrație să „pară corectă”. Evaluarea trebuie să
poată spune ce s-a întâmplat, ce putea observa operatorul, ce știau
participanții, ce trebuia memorat, ce acțiuni erau permise și de ce verdictul
este `PASS` sau `FAIL`.

Un sandbox este complet numai dacă include:

- produsul evaluat: Odoo PMORG, memoria reală și runtime-ul aflat la test;
- o lume sintetică materializată în Odoo real;
- adevăr privat și rezultate așteptate păstrate în afara produsului;
- participanți scriptați sau personas, conectați prin contractul final de
  canal;
- timp virtual și defecte injectabile;
- trasă publică append-only, corpus, scorer și verdict reproductibil;
- izolare față de producție și resetare prin distrugerea volumelor.

O instanță Odoo cu PostgreSQL și câteva date demo este un **substrat de
sandbox**, nu un sandbox de evaluare complet.

## 2. Ce este evaluat și ce este de încredere

### 2.1 System under test

`SUT` — system under test — cuprinde exact artefactele cărora li se acordă
verdictul. Scope-ul său este declarat în manifest și crește pe gate-uri:

| Gate | `sut_scope` | Harness, fără credit în verdictul produsului |
|---|---|---|
| A | Odoo + addon-urile PMORG | kernelul de evaluare: manifest, clock, oracle, recorder, scorer și controale anti-leak |
| B–D | Odoo + addon-urile PMORG + memoria/adaptorul MCP | runnerul de referință, canalul și actorii scriptați |
| E | Odoo + memorie + agentul/modelul operator | canalul, personas și evaluatorul |
| F1 | Odoo + memorie + Hermes/adaptorul său | agent determinist de referință, canal și actorii scriptați |
| F2 | Odoo + memorie + Hermes/adaptor + agentul/modelul operator înghețat la Gate E | canalul, personas și evaluatorul |

La Gate C–D runnerul determinist este un driver de referință: demonstrează
contractele și bucla posibilă, dar nu primește merit pentru inteligența
operatorului. La Gate F1 se califică runtime-ul Hermes cu un agent de
referință; la F2 se califică produsul integrat Hermes + operatorul AI înghețat
la Gate E, fără schimbarea Odoo, a memoriei, a scenariilor sau a scorerului.
Personas nu fac niciodată parte din SUT; ele sunt stimuli controlați.

### 2.2 Trusted evaluation harness

Harness-ul de încredere conține controllerul de rulare, ceasul virtual,
generatorul de lume, injectorul de evenimente, simulatorul de canal,
runtime-ul personas, oracolul, colectorul și scorerul. Faptul că harness-ul
este de încredere nu îi permite să ofere SUT-ului răspunsurile corecte.

Principiul central este:

> Produsul vede numai lumea publică și conversațiile livrate. Persona vede
> numai fișa sa și adevărul ei privat. Scorerul vede totul numai pentru a
> evalua. Nicio cale de rețea, credențial sau artefact comun nu inversează
> această separare.

### 2.3 Matricea de autoritate

| Componentă | Poate citi | Poate scrie | Nu poate accesa |
|---|---|---|---|
| Odoo PMORG | propria bază, comenzile autorizate | starea formală Odoo | oracle DB, memory DB direct, secrete LLM |
| Memorie MCP | evidențe admise, ancore și citiri Odoo permise | propria bază de memorie | adevăr privat, rezultate așteptate, SQL Odoo |
| Runtime/operator | API Odoo, MCP, mesaje livrate, ceas public | numai comenzi înguste Odoo/MCP/canal | oracle DB, DB-urile interne, manifestul secret |
| Participant scriptat/persona | fișa publică și slice-ul privat al identității sale | răspunsuri prin canal | memoria PMORG, adevărul altor personas, scorerul |
| Channel simulator | envelope-uri și politica de livrare | inbox/outbox de test | sensul oracle, DB-urile SUT |
| Worldgen/environment injector | scenariul secret și API-ul de fixture | Odoo numai prin identitatea tehnică de harness; oracle | memoria și conversația operatorului |
| Synthetic user driver | acțiunea publică programată și propriile drepturi Odoo | numai prin identitatea/ACL-ul utilizatorului sintetic | oracle, admin/fixture API și alte identități |
| Recorder public | evenimentele observabile ale runului | trasă append-only | modificarea SUT sau a oracolului |
| Checkpoint exporter | proiecții read-only Odoo/memorie la bariera tick-ului | snapshoturi sigilate append-only | scrieri în SUT, labels și adevăr privat |
| Scorer | oracle, trasă, exporturi read-only Odoo/memorie | scoruri și verdict | modificarea retroactivă a runului |

Worldgen primește privilegiul de inițializare numai în fazele `seed` și
`inject`. După fiecare operație, credențialul este revocat sau serviciul se
oprește. Scorerul rulează după quiescence și nu poate „repara” rezultatul.

## 3. Topologia completă

```text
                              loopback/SSH tunnel
                                      │
                                ┌─────▼─────┐
                                │  gateway  │
                                └─────┬─────┘
                                      │ API/UI permis
                 ┌────────────────────┴────────────────────┐
                 │                SUT plane                │
                 │  ┌──────────┐      ┌───────────────┐    │
                 │  │ Odoo     │◄────►│ agent/Hermes  │    │
                 │  └────┬─────┘      └──────┬────────┘    │
                 │       │       Gate E/F1/F2│ MCP          │
                 │  ┌────▼─────┐      ┌──────▼────────┐    │
                 │  │ Odoo DB  │      │ memory API/DB │    │
                 │  └──────────┘      └───────────────┘    │
                 └────────────────────┬────────────────────┘
                                      │ channel contract
                    ┌─────────────────▼──────────────────┐
                    │ public harness plane              │
                    │ reference runner · virtual clock  │
                    │ channel simulator · personas      │
                    └─────────────────┬──────────────────┘
                                      │ scoped capabilities
                    ┌─────────────────▼──────────────────┐
                    │ private evaluation plane          │
                    │ worldgen · oracle DB · recorder   │
                    │ scorer · artifact store           │
                    └────────────────────────────────────┘

             operator model ─┐
                             ├─► controlled LLM proxy ─► allow-listed provider
             persona model ──┘       (Gate E/F2; contexts separate)
```

### 3.1 Servicii

| Serviciu | Responsabilitate |
|---|---|
| `gateway` | singurul port publicat, numai pe loopback; UI și API explicit permise |
| `odoo`, `odoo-db` | ontologia executabilă și registrul formal; bază și filestore curate per run |
| `memory-api`, `memory-db` | memoria reală prin MCP și persistența ei separată |
| `reference-runner` | driver determinist al Gate C–D; implementează contractul fără a fi creditat drept produs |
| `runtime` | agentul/operatorul la Gate E; Hermes/adaptorul la F1; integrarea ambelor la F2 |
| `run-controller` | mașina de stare a runului, tick-uri și activarea evenimentelor |
| `virtual-clock` | timpul logic unic; nu modifică ceasul hostului |
| `channel-sim` | transport, identitate, corelare, latență, tăcere, duplicate și ordine |
| `persona-runtime` | actori scriptați sau LLM cu acces privat limitat per identitate |
| `worldgen` | creează starea inițială Odoo și adevărul corespunzător |
| `world-driver` | injectează evenimente externe ale lumii prin comenzi de harness; nu simulează acțiuni umane |
| `synthetic-user-driver` | execută modificări manuale programate sub utilizatorul Odoo sintetic și ACL-urile lui reale |
| `oracle-api`, `oracle-db` | ground truth, așteptări, split secret și maparea către obiectele Odoo |
| `trace-recorder` | envelope-uri observabile append-only și hash chain per run |
| `checkpoint-exporter` | sigilează proiecțiile Odoo și memorie la fiecare checkpoint/high-water mark |
| `scorer` | calculează metrici, verifică invariante și emite verdictul |
| `llm-proxy` | unicul egress LLM la Gate E/F2; allow-list, bugete, redacție și jurnal complet |

Serviciile pot fi împachetate împreună la început, dar **limitele de
autoritate, bazele și credențialele nu se comprimă**. Două procese în același
container sunt acceptabile numai dacă nu transformă oracolul într-un fișier
citibil de SUT.

### 3.2 Rețele și egress

| Plan | Participanți | Regulă |
|---|---|---|
| `ingress` | gateway | singura publicare este `127.0.0.1`; accesul remote se face prin tunel SSH |
| `odoo` | Odoo, Odoo DB, runtime, worldgen/injector controlat, checkpoint-exporter | DB nu publică port; runtime-ul nu primește SQL; exporterul are numai API/rol SQL read-only allow-listed |
| `memory` | memory API/DB, runtime, adaptor Odoo read, checkpoint-exporter | memory DB nu este accesibilă runtime-ului sau Odoo; exporterul are numai API/rol SQL read-only allow-listed |
| `channel` | runtime, channel-sim, persona-runtime | numai contractul de mesaje; fără oracle DB |
| `oracle` | oracle DB/API, worldgen, persona scope broker, scorer | rețea internă absentă complet din containerele SUT |
| `telemetry` | recorder, checkpoint-exporter și store append-only | observație read-only/write-only către store; niciun feedback în decizii |
| `egress` | numai llm-proxy | dezactivat la Gate A–D și F1; allow-list explicit la Gate E/F2 |

PostgreSQL pentru Odoo, PostgreSQL/pgvector pentru memorie și baza oracolului
folosesc servicii, volume, roluri și parole distincte. O bază cu trei scheme
nu oferă separarea necesară pentru un benchmark credibil.

Orice endpoint Odoo/memorie este obligatoriu și legat de `run_id`, profil,
instance UUID și o allow-list de hosturi sandbox. Configurația absentă sau o
țintă care nu aparține runului oprește serviciul. Aceasta este o condiție
concretă de migrare: `aipm/config.py` are în snapshotul curent valori
implicite către un mediu extern și ingest activ implicit. Componenta nu poate
intra în imaginea de evaluare până când aceste defaulturi sunt eliminate,
ingestul pornește `false`, iar secretele și DSN-ul sunt furnizate fail-closed,
individual, pentru run.

Containerele nu primesc Docker socket, `host` network/PID/IPC, mod
`privileged`, device-uri sau capabilități nejustificate. Rulează non-root unde
runtime-ul permite, cu `no-new-privileges`, `cap_drop`, profil seccomp,
filesystem root read-only și volume writable înguste. Fiecare serviciu are
limite CPU/memorie/PID și healthcheck; oprirea prin resource exhaustion este
eveniment observabil, nu acces la host. Compose networking este dublat de
firewall/egress deny pe host și de probe negative de reachability.

Secretele sunt fișiere individuale sau mecanism echivalent, cu suport
`*_FILE`; nu apar în argumentele procesului, labels, logs ori DSN-uri
inspectabile. Odoo folosește `dbfilter` exact, database manager dezactivat și
rol SQL fără superuser/`CREATEDB`/`CREATEROLE`. Bootstrap owners și
credențialele de fixture sunt eliminate înainte de `PREFLIGHT_PASSED`.

## 4. Unitatea reproductibilă: run bundle

Un sandbox este o instanță efemeră. Un **run bundle** este definiția imuabilă
și artefactul reproductibil al evaluării.

Fiecare execuție primește `run_id` unic. Câmpurile care definesc intrarea
produc separat `evaluation_input_hash`; un replay are `replay_of=<run_id
inițial>`, același input hash și volume noi, nu reutilizează identitatea sau
starea execuției vechi.

Bundle-ul are două manifeste:

- `manifest.public.yaml`: versiuni, profil, referință de caz, politici, ceas,
  contracte și, pentru suite neascunse, seed-ul public; în hidden-test
  referința este opacă și nu divulgă familia incidentului; este vizibil
  SUT-ului;
- `manifest.oracle.yaml`: incidentele complete, adevărul privat, disclosure
  rules, splitul, seed-ul hidden, fault schedule secret și așteptările; este
  montat numai în planul privat.

Manifestul public are hash propriu. Manifestul oracle este legat de run prin
un commitment care nu poate fi enumerat: `HMAC-SHA256` cu o cheie a
evaluatorului sau `SHA-256(canonical_manifest || nonce)` cu nonce aleator de
minimum 256 biți. SUT primește numai commitment-ul, niciodată hash-ul simplu
al seed-ului ori al unui payload secret cu entropie mică. Cheia/nonce-ul rămân
în oracle pe durata vieții release-ului hidden; custodele poate verifica HMAC
sau revela nonce-ul unui auditor după retragerea release-ului. Conținutul
secret nu apare în numele fișierelor, variabile de mediu, logs sau labels
Docker.

Exemplu abreviat de manifest public:

```yaml
schema_version: pmorg.eval.run/v1
run_id: 01J...
purpose: qualification          # development | calibration | qualification
sut_scope: [odoo-pmorg, memory, operator-model]
suite: {id: longitudinal-core, version: 1.0.0}
case_ref: hidden:7f3a...         # scenariul descriptiv rămâne în oracle
profile: {id: ORG-DIST, version: 1.0.0}
oracle_commitment: hmac-sha256:... # acoperă seedul și manifestul secret
artifacts:
  pmorg: sha256:...
  odoo: 1b8f6802832cfa4d146193a912af1f4445d09f0a
  memory: sha256:...
  runtime: sha256:...
harness:
  worldgen: sha256:...
  controller: sha256:...
  channel_sim: sha256:...
  scorer: sha256:...
contracts:
  odoo_api: 1.0.0
  memory_mcp: 1.0.0
  channel: 1.0.0
clock: {start: 2026-01-05T08:00:00Z, step: PT5M, timezone: Europe/Bucharest}
policies: {autonomy: approval-first-v1, monitoring: standard-v1}
models: {}                       # gol la Gate A–D și F1
```

La Gate E/F2, manifestul fixează separat pentru operator, personas, extracția
memoriei, embeddings și orice grader semantic providerul, identificatorul
modelului, snapshotul dacă există, parametrii, prompt template hash, tool
schema hash, bugetul și politica de retry. Fiecare apel reține
request/response hash, usage, latență și identificatorul furnizorului. Lipsa
unei componente din `sut_scope`, `artifacts`, `harness` sau `models` face
manifestul invalid.

„Același build” din Gate C2 înseamnă aceleași digesturi pentru PMORG,
memorie, runtime și imaginile de bază. Profilul selectează module, pack-uri și
date; nu selectează alt artefact executabil.

## 5. Proprietatea datelor

Scorarea separă explicit șase stări care nu sunt interschimbabile:

```text
W(t)    adevărul fizic injectat al lumii
O(t)    starea formală vizibilă în Odoo
K(p,t)  ce știe sau crede participantul p
E(t)    evidența ajunsă legitim la PMORG până la t
A(t)    autoritatea și delegările valabile la t
M(t)    starea efectivă a memoriei PMORG
```

PMORG nu este recompensat pentru ghicirea lui `W(t)` înainte ca informația
să intre în `E(t)`. O afirmație adevărată fizic poate rămâne ipoteză până la
evidență/validare și nu devine automat adevăr formal `O(t)`. Extracția se
compară cu `E(t)`, formalizarea cu `O(t)` și `A(t)`, clarificarea cu atomii
relevanți din `K(p,t)`, iar continuitatea cu istoricul `M(t)`.

### 5.1 Odoo — adevărul formal curent

Odoo păstrează obiectele reale ale organizației sintetice: identități,
proiecte, taskuri, transferuri, angajamente, aprobări și rezultate. Worldgen
le creează prin ORM/API-uri Odoo și fluxuri de business, nu prin SQL direct.
Ancorele testate sunt astfel aceleași ancore pe care produsul le-ar folosi.

Odoo nu primește:

- eticheta „răspuns corect”;
- ce știe în secret o persona;
- claims pe care memoria ar trebui să le extragă;
- pragurile și verdictul benchmarkului.

### 5.2 Memoria — numai informația legitim observată

Memory DB conține exact evidențele, candidații, claims, contradicțiile,
supersession și referințele pe care SUT le-a produs prin MCP. Nu primește
snapshotul lumii, tabelele oracle sau conversațiile nelivrate. Citirea live
din Odoo se face numai prin ancore și scope-ul negociat.

### 5.3 Oracle DB — adevărul evaluării

Modelul logic minim este:

| Entitate | Conținut minim |
|---|---|
| `evaluation_run` | run ID, suite/scenario/profile versions, split, seed, digesturi, stare, manifest hash |
| `world_object` | cheia sintetică stabilă și referința Odoo instance/model/res_id creată la seed |
| `world_fact` | afirmație structurată, sursă, interval de valabilitate și vizibilitate publică |
| `world_event` | timp virtual, actori, cauză, efect formal, urmă Odoo așteptată |
| `private_fact` | persona, ce știe/a făcut, interval, disclosure rule și eventuală contradicție |
| `expected_unit` | informație/acțiune ce trebuie extrasă, ancorată, urmărită sau evitată |
| `expected_memory` | tip, claim normalizat, ancore, autor, validitate, status și supersession așteptat |
| `expected_operator_action` | obligație, fereastră de timp, politică, aprobare și rezultat acceptabil |
| `fault_event` | defect, țintă, moment, durată și comportament de recovery așteptat |
| `observed_event` | envelope public capturat, ordine, correlation/causation și hash chain |
| `metric_result` | metrică/version, numărător, numitor, valoare, prag și referințe de evidență |
| `evaluation_verdict` | validitate, rezultat, hard failures, raport hash și semnătură |

`expected_unit` descrie sensul necesar, nu o frază exactă. Un răspuns corect
semantic nu e penalizat pentru că diferă lexical de textul generatorului.
Matcher-ele deterministe, seturile de sinonime și eventualul grader semantic
sunt versionate și evaluate separat.

Identitatea cross-service folosește un `logical_entity_id` stabil, distinct
de `res_id` Odoo, care se poate schimba după reset. O referință completă are
cel puțin `logical_entity_id`, `odoo_instance_uuid`, `company_id`, `model`,
`res_id`, `anchor_type`, `schema_version` și `observed_write_date`. Evenimentele
folosesc `event_seq` + `sim_time` pentru evaluare și `recorded_at` numai pentru
auditul real; toate comparațiile temporale sunt `as_of_event_seq`.

Un `expected_memory` se activează numai după ce evidența minimă necesară a
fost efectiv livrată SUT-ului. Un fapt privat nedivulgat nu poate genera un
false negative împotriva memoriei. Gold labels leagă explicit memoria
așteptată de autor, ancore, evidențe, validitate și muchia de supersession;
aceasta nu este inferată doar dintr-un status.

### 5.4 Trasa și artefactele

Recorderul produce un flux append-only cu envelope comun:

```text
event_id, run_id, virtual_time, wall_time, source, event_type,
correlation_id, causation_id, subject_refs, payload_ref, schema_version,
previous_hash, event_hash
```

Payloadurile mari, transcripturile, exporturile Odoo/memorie și apelurile de
model sunt content-addressed în artifact store. Orice redacție produce un
artefact nou; nu suprascrie originalul. Raportul citează ID-urile dovezilor,
nu doar un scor agregat.

La fiecare checkpoint, controllerul oprește avansarea timpului, așteaptă
high-water marks pentru outbox/inbox/canal și pornește `checkpoint-exporter`
cu roluri read-only. Exporterul sigilează proiecțiile allow-listed Odoo și
memorie cu `as_of_event_seq`, capability descriptor hash și snapshot hash
înaintea tick-ului următor. Starea finală nu poate înlocui aceste stări
istorice. Ca alternativă viitoare, un event log poate elimina snapshoturile
numai după ce un test demonstrează reconstrucția completă și identică a
proiecției fiecărui checkpoint.

Fiecare bundle oracle conține și un canary unic, absent din fixture-ul public.
Canary-ul este căutat în outputurile, logurile și memoria SUT; apariția lui
invalidează runul și demonstrează o scurgere de frontieră.

## 6. Worldgen organization-agnostic

Generatorul nu este „un simulator HoReCa” în nucleu. El are două niveluri:

```text
worldgen core
  identități · structură · calendar · inițiative · proiecte · taskuri
  evenimente · incidente · timp virtual · mapare Odoo/oracle

domain packs
  project-minimal · professional-services · distribution · horeca · ...
```

Un profil organizațional selectează modulele Odoo, anchor packs, worldgen
packs, rolurile, politicile și parametrii. Profilurile canonice obligatorii
sunt:

| Profil | Odoo / worldgen | Ce demonstrează |
|---|---|---|
| `ORG-MIN` | `project` + core | produsul funcționează fără HR și domenii opționale |
| `ORG-SERV` | `project`, `hr` + professional-services | roluri, livrabile, termene și angajamente externe |
| `ORG-DIST` | `project`, `hr`, `stock` + distribution | incidente operaționale și ancore Inventory reale |

ID-urile de mai sus sunt canonice în manifeste și evenimente. Fișierele lor
folosesc slugurile `org-min.yaml`, `org-serv.yaml` și `org-dist.yaml` sub
`evaluation/profiles/`; numele `project-minimal`, `professional-services` și
`distribution` desemnează worldgen packs, nu profile.

`horeca` este un domain pack compozit ulterior, util pentru volum și
interacțiunea dintre POS, stoc, achiziții, contabilitate și HR. Bistro,
restaurant și lanț sunt profile de configurare peste acel pack, nu ramuri de
cod și nu înlocuiesc cele trei probe de agnosticism.

Fiecare scenariu definește:

1. starea inițială materializată în Odoo;
2. incidente cu adevăr complet cunoscut;
3. ce este vizibil în Odoo la fiecare moment;
4. ce știe privat fiecare participant;
5. când și în ce condiții informația poate fi divulgată;
6. obligațiile și acțiunile permise operatorului;
7. rezultatul și dovezile acceptabile.

Worldgen poate produce variație din seed, dar forma incidentului și
distribuția parametrilor sunt versionate. Seed-ul singur nu este o versiune.
Fiecare pack folosește un stream RNG derivat din `(seed, pack, entity_kind)`,
astfel încât adăugarea unui pack să nu renumeroteze lumea existentă. Buildul
produce `world.lock` cu versiunile pack-urilor și hash-ul planului; două
materializări deterministe ale aceluiași lock trebuie să producă același hash
al proiecției canonice Odoo, independent de ID-urile secvențiale PostgreSQL.

## 7. Participanți și canal

### 7.1 Două moduri de participant

- **scripted actor** pentru Gate C–D, E1 și F1, precum și F2-E1: răspunsurile
  și tranzițiile sunt deterministe; acesta izolează logica PMORG și modelul
  operator de variația unui LLM interlocutor;
- **LLM persona** pentru E2 și replicile E3 aferente, inclusiv F2-E2/E3:
  produce limbaj și comportament variabil în limitele fișei publice și ale
  adevărului privat primit.

O persona primește numai:

- propria identitate, autoritate și relațiile publice;
- stilul de comunicare;
- evenimentele pe care le-a observat;
- propriile `private_fact` și disclosure rules;
- mesajele care i-au fost livrate.

Nu primește schema de scoring, expected units, adevărul altor personas,
conținutul memoriei sau acces generic la Odoo. Brokerul oracle emite un token
scurt, limitat la `(run_id, persona_id)`; compromiterea unei personas nu
dezvăluie întregul benchmark.

Înaintea generării lingvistice, un disclosure guard determinist selectează
numai faptele pe care persona le poate divulga în acel turn. Un validator de
conformitate verifică ulterior că persona nu a inventat cunoaștere din afara
slice-ului său. Cauza este clasificată prin reguli predeclarate:

- dacă operatorul încearcă să eludeze disclosure guard, să extragă adevăr
  interzis sau trimite o comandă/prompt nepermis, tentativa este eveniment de
  siguranță al SUT și poate produce `QUALITY/FAIL`; runul nu este invalidat
  pentru a-i șterge efectul din denominator;
- dacă persona inventează ori divulgă spontan din cauza simulatorului, fără
  stimul interzis al SUT, runul este `INVALID_SIMULATOR`, nu eroare PMORG.

Clasificarea, retry-urile, coada de seed-uri de înlocuire și pragul maxim de
`INVALID_SIMULATOR` se fixează înaintea suitei. Runul original rămâne în audit
și în metrica de sănătate a harnessului; nu se selectează post-hoc numai
replicile favorabile.

Modelul operator și modelul personas au contexte, prompturi, chei și jurnale
separate chiar dacă folosesc același provider. Nu se folosește o conversație
LLM comună pentru ambele roluri.

### 7.2 Canalul simulat este implementarea contractului final

`channel-sim` nu este un shortcut de tip apel direct între două funcții. El
implementează identitate, thread, message ID, correlation ID, delivery
receipt, reply-to, retry și idempotency. Politica scenariului poate produce:

- latență și non-răspuns;
- duplicate;
- livrare out-of-order;
- mesaj fără corelare;
- indisponibilitate temporară;
- răspuns după expirarea unui lease sau după schimbarea planului.

Niciun email, număr de telefon, tenant Teams/Slack/Telegram sau cont real nu
este folosit. Un canal extern apare numai într-un mediu de test separat și
trebuie să treacă aceeași suită de contract.

## 8. Timp virtual și defecte

Ceasul virtual este autoritatea pentru termene, `next_check_at`, latențe,
ferestre de aprobare și succesiunea incidentelor. Nu se schimbă ceasul
hostului și nu se falsifică arbitrar `create_date` Odoo.

PMORG păstrează separat:

- `declared_occurred_at`: timpul declarat de actor/sursă, neautoritativ;
- `effective_at`: timpul de business rezolvat din tick-ul trusted în test;
- `recorded_at`: timpul real al persistării, pentru auditul tehnic.

Controllerul avansează timpul numai când serviciile au confirmat quiescence
pentru tick-ul curent. `virtual-clock` emite o capabilitate neforjabilă
`tick_id` legată de `run_id`, `event_seq` și `sim_time`; runtime-ul o poate
prezenta, dar nu o poate crea sau avansa. Odoo, memoria și canalul validează
capabilitatea și rezolvă `effective_at` server-side. Un câmp `now` sau
`occurred_at` furnizat de SUT rămâne metadată declarată și nu decide deadline,
lease, tăcere ori ordine. În producție aceeași abstracție folosește timpul de
sistem server-side și nu expune capabilitatea de time travel.

Un test nu depinde de `sleep`. Toate schedulerele aflate în scope acceptă
sursa de timp injectată; o utilizare directă a ceasului de sistem în logica
longitudinală este defect de contract.

Catalogul minim de fault injection include:

- restart Odoo, memorie și runtime;
- timeout și indisponibilitate MCP/canal;
- eveniment sau comandă duplicată;
- răspuns întârziat ori necorelat;
- lease expirat și worker concurent;
- modificare manuală Odoo între citire și scriere, executată prin
  `synthetic-user-driver`, nu prin identitatea privilegiată worldgen;
- registry/anchor pack incompatibil;
- ancoră arhivată sau obiect schimbat;
- claim contradictoriu și decizie superseded;
- răspuns LLM invalid, tool call interzis și epuizarea bugetului.

Fault schedule-ul de calificare este ascuns SUT-ului, dar fiecare injecție
este ulterior vizibilă în raport și reproductibilă.

## 9. Corpusul și separarea train–test

Corpusul unui run unește, după închiderea lui:

```text
trasa publică
+ snapshoturi Odoo și memorie la checkpointuri
+ outputurile reale ale memoriei și operatorului
+ adevărul oracle și etichetele normalizate
+ scorurile și verdictul
```

Snapshoturile sunt consumate de scorer, nu ingerate de memorie. Corpusul este
versionat și împărțit înaintea calibrării:

| Partiție | Utilizare | Acces la etichete |
|---|---|---|
| `train` | exemple, eventual fine-tuning | echipa de dezvoltare |
| `calibration` | prompturi, matchere, praguri și politici | echipa de dezvoltare |
| `hidden-test` | verdict de calificare | numai scorerul privat |

Splitul se face la nivel de **familie de scenariu, template de incident și
linie de proveniență**, nu pe turnuri individuale. Variantele aceluiași
incident nu pot apărea simultan în train și hidden-test. Prompts, thresholduri
și codul scorerului se îngheață înainte de deschiderea rezultatului hidden.

Catalogul separă patru lucruri:

- `case_version`: lumea, incidentul, personas și gold labels imuabile;
- `benchmark_run`: execuția unui build SUT pe acel caz;
- `corpus_example`: fereastra derivată pentru o funcție concretă;
- `corpus_release`: selecția versionată, sealed și content-addressed.

Corectarea unei etichete produce o versiune nouă și `supersedes`; nu modifică
release-ul existent. Toate exemplele cu același `leakage_group_id` moștenesc
același split. Fiecare încercare hidden-test este auditată, iar un set hidden
expus este retras, nu refolosit sub alt nume.

O eroare dintr-un pilot nu copiază automat conversația sau datele reale în
corpus. Ea intră întâi în carantină, este reprodusă ca scenariu sintetic cu
adevăr consemnat, verificată pentru absența datelor identificabile și apoi
primește o partiție într-o versiune viitoare a suitei.

## 10. Scoring și verdict

### 10.1 Niveluri de evaluare

| Nivel | Exemple de măsurători |
|---|---|
| infrastructură | digesturi, izolare, reset, health, registry handshake, oracle inaccesibil |
| memorie | extracție, ancorare, fapt/ipoteză, contradicție, supersession, recall |
| operator | clarificare, plan/task, confirmare, follow-up, replanificare, escaladare, verificare |
| longitudinal | continuitate după restart, termen, tăcere, revenire după N zile |
| siguranță | acces refuzat, acțiune neautorizată, idempotency, lipsa efectelor duplicate |
| agnosticism | același build, trei profile, zero concepte pentru module absente |
| robustețe AI | rată de succes și variație pe replici, tool calls invalide, buget |

Fiecare metrică are în `metrics.yaml`: versiune, populație, match rule,
numărător, numitor, cazuri `must`, prag și dovezile cerute. Cazurile `must`
trebuie să treacă 100%. Pragurile agregate se stabilesc prin calibrare și nu
se schimbă retroactiv după vizualizarea hidden-test.

Matchingul gold–actual este one-to-one la checkpoint: același item observat
nu poate satisface simultan mai multe memorii așteptate. Recalcularea cu o
versiune nouă de scorer creează un `scoring_run` nou și păstrează rezultatul
vechi; nu rescrie istoria benchmarkului.

Invariantele, autoritatea, ancorele, idempotency și stările se scorează
structural, fără LLM judge. Un grader semantic poate furniza o măsurătoare
auxiliară de limbaj, dar nu decide gate-uri de siguranță sau corectitudine.

### 10.2 Validitate și calitate sunt diferite

Verdictul are două axe:

```text
run_validity: VALID | INVALID
quality_result: PASS | FAIL | NOT_SCORED
```

Un run este `INVALID`, nu „slab”, dacă artefactele nu corespund manifestului,
preflightul a eșuat, trasa este incompletă, SUT a putut accesa oracle sau
scenariul nu a rulat integral. `PASS` există numai pentru un run valid care
trece toate invariantele hard și pragurile versiunii de suită. Waiver-ele nu
transformă un fail în pass; ele cer o suită nouă și o decizie explicită.

La Gate E/F2, politica de replici declară numărul țintă, seed-urile primare,
o coadă ordonată de replacement, numărul maxim de retry per cauză și pragul
de invaliditate al simulatorului. Fiecare `INVALID` rămâne în raport;
replacementul nu îl șterge. Depășirea pragului invalidează calificarea
harnessului, iar o provocare interzisă produsă de SUT rămâne quality failure,
nu este convertită în invaliditate.

Raportul final conține:

- manifest hash și toate digesturile;
- validitatea și verificările de izolare;
- scorul per metrică și profil;
- hard failures și exemplele concrete;
- timeline-ul inițiativă → conversație → memorie → acțiune → rezultat;
- costurile și variația modelelor la Gate E/F2;
- hash-ul artefactelor și comanda exactă de reproducere.

### 10.3 Scorerul trebuie el însuși testat

Înaintea calificării, harness-ul rulează controale negative:

- un adaptor `null-memory` trebuie să rateze cazurile `must`;
- o mutație care ancorează deliberat pe obiectul greșit trebuie detectată;
- o comandă duplicată trebuie să eșueze dacă produce două efecte;
- un probe container din SUT nu trebuie să poată rezolva sau conecta oracle;
- o trasă modificată trebuie să rupă hash chain-ul;
- un fixture de referință minim trebuie să producă scorul așteptat.

Se rulează și teste metamorfice: redenumirea organizației, adăugarea de
înregistrări irelevante, mutarea epoch-ului virtual și reordonarea
duplicatelor nu trebuie să schimbe verdictul semantic.

Un scorer care nu poate respinge variante defecte nu poate acorda un verdict
credibil.

Pentru Gate E/F2, o singură rulare stochastică nu califică sistemul. Suita
declară dinainte numărul de replici, seed-urile și replacement policy;
raportul publică distribuția, intervalul de încredere și rata/cauzele
runurilor invalide. Replay-ul răspunsurilor LLM este permis pentru debugging
determinist, nu înlocuiește calificarea pe apeluri reale.

## 11. Ciclul de viață al unui run

```text
DEFINED
  → PROVISIONED
  → SEEDED
  → PREFLIGHT_PASSED
  → RUNNING
  → QUIESCED
  → CAPTURED
  → SCORED
  → ARCHIVED
  → DESTROYED
```

Orice abatere de integritate produce `INVALID`; un eșec de calitate după
`CAPTURED` produce `VALID/FAIL`. Pașii sunt:

1. build o singură dată și consemnarea digesturilor;
2. generarea manifestelor public și secret, apoi închiderea lor la scriere;
3. provisionarea rețelelor, credențialelor și volumelor curate;
4. seed Odoo + oracle și oprirea worldgen;
5. negocierea capability registry Odoo–memorie–runtime;
6. preflight de izolare, versiuni, baze curate, ceas și probe anti-leak;
7. rularea tick-urilor, mesajelor, incidentelor și defectelor; înaintea
   fiecărui tick nou se ating high-water marks și se sigilează checkpointurile
   Odoo/memorie pentru `as_of_event_seq`;
8. quiescence: oprirea stimulilor și golirea controlată a cozilor;
9. exporturi read-only, închiderea trasei și calculul hash-urilor;
10. scoring, verdict și raport;
11. arhivarea bundle-ului rezultat;
12. distrugerea containerelor, rețelelor și volumelor efemere.

Resetarea pentru un nou run înseamnă `down --volumes` și credențiale noi, nu
ștergerea selectivă a rândurilor. Imaginile pot fi reutilizate după digest;
starea nu.

Gate A–D trebuie să fie deterministe la nivelul evenimentelor și scorurilor
pentru același bundle. Egalitatea se calculează pe o proiecție semantică
canonică ce exclude `run_id`, wall time, UUID-urile de execuție, `res_id`
secvențiale și alte câmpuri tehnice nondeterministe. Hash chain-ul integral
este unic fiecărui run și dovedește integritatea lui, nu identitatea byte cu
un replay. Gate E/F2 este reproductibil ca configurație și trasă, dar este
calificat statistic, nu prin pretenția că un provider LLM va returna aceiași
bytes.

## 12. Legătura cu gate-urile PMORG

| Gate | Configurația sandboxului | Dovada principală |
|---|---|---|
| A | Odoo real, manifest, clock, oracle, recorder; fără LLM | schemă, contracte, instalare, izolare și reproducere |
| B-min | + memory API/DB real pe profil minimal | milestone provizoriu pentru admitere, proveniență, temporalitate și supersession |
| B | aceeași suită de memorie pe fiecare registry de profil | Gate complet înaintea C2; un profil/pack nou îl redeschide pentru acel registry |
| C1 | + runner și actori scriptați, profil distribuție | bucla completă deterministă |
| C2 | același bundle de artefacte pe minimal/services/distribution | agnosticism organizațional fără contaminare între baze |
| D | + 30–60 zile virtuale și fault schedule | persistență, follow-up, recovery și adaptare |
| E1 | model operator + actori scriptați | izolează calitatea operatorului AI |
| E2 | model operator + LLM personas | conversație realist variabilă cu adevăr privat |
| E3 | replici și seed-uri predeclarate | robustețe statistică și cost |
| F1 | Hermes + agent determinist în locul runnerului | echivalență de contract și longitudinalitate a runtime-ului |
| F2 | Hermes + operatorul AI înghețat la E | produsul integrat trece E1–E3 fără schimbarea scenariilor/scorerului |

Subgate-urile E1–E3 și F1–F2 detaliază Gate E/F; nu schimbă ordinea A–F.

## 13. Definition of Done al sandboxului complet

Sandboxul de evaluare, ca produs tehnic separat de verdictul PMORG, este gata
când:

1. o singură comandă provisionază, rulează, raportează și distruge un run;
2. nicio componentă nu folosește date, identități, canale sau credențiale de
   producție;
3. orice URL, DB, instance UUID și namespace lipsă sau nealiniat cu runul
   oprește pornirea; nu există defaulturi de producție;
4. numai gateway-ul este publicat pe loopback, iar PG/Odoo/memorie/oracle nu
   au porturi publice;
5. niciun container nu are Docker socket, mod privilegiat, host namespaces
   sau capabilități nejustificate; limitele de resurse și hardeningul sunt
   verificate;
6. SUT nu are rută, DNS, mount, secret sau API către oracle; probele negative
   demonstrează asta;
7. Odoo, memoria și oracle au baze, roluri și volume distincte;
8. run bundle-ul fixează toate artefactele, contractele, profilele, seed-urile,
   modelele și politicile;
9. worldgen materializează în Odoo și poate reconstrui identic profilele
   deterministe;
10. ceasul virtual și channel-sim nu depind de sleep sau de servicii reale,
    iar SUT nu poate emite/avansa `tick_id`;
11. trasa este append-only, completă și legată criptografic;
12. checkpointurile istorice Odoo/memorie sunt sigilate înaintea tick-ului
    următor și pot susține orice scor `as_of_event_seq`;
13. scorerul citează dovezi și respinge controalele intenționat defecte;
14. corpusul are splituri fără leakage și hidden labels inaccesibile SUT;
15. un run întrerupt nu poate primi `PASS`;
16. resetarea distruge toate volumele și emite credențiale noi;
17. aceeași comandă reproduce un Gate C–D eșuat din bundle-ul arhivat;
18. documentația spune explicit ce este implementat și ce rămâne proiectat.

Aceste condiții certifică **instrumentul de evaluare**. Ele nu certifică
automat PMORG; produsul primește verdict numai prin gate-urile din §12.

## 14. Structura de repo propusă

```text
evaluation/
  contracts/                 # schemas pentru manifest, event și report
  profiles/                  # org-min.yaml, org-serv.yaml, org-dist.yaml
  scenarios/                 # familii și versiuni, fără hidden labels publice
  worldgen/
    core/
    packs/
  personas/
    scripted/
    templates/
  channel/
  controller/
  clock/
  user_driver/
  oracle/
    migrations/
  recorder/
    checkpoints/
  scorer/
    metrics/
    controls/
  tests/
deploy/evaluation/
  compose.yaml
  config/
  scripts/
artifacts/evaluation/         # gitignored; run bundles și rapoarte locale
```

Hidden-test definitions nu sunt comise în repository-ul accesibil SUT. Repo
conține schema, exemple publice și suitele train/calibration; calificarea
montează un bundle secret read-only în planul oracle.

## 15. Ordinea de construcție

| Etapă | Livrabil | Nu pretinde încă |
|---|---|---|
| S0 — substrat | Odoo/PG/gateway izolate, surse fixate, reset și verificări de infrastructură | memorie, oracol sau evaluare funcțională |
| S1 — nucleu PMORG | prima felie din `04-NEXT-SESSION.md`, profil minimal instalabil | buclă operator |
| S2 — kernel de evaluare | manifest, oracle, clock, recorder, channel-sim, scorer, controale anti-leak și Gate A | realism LLM |
| S3 — memorie | memory API/DB real, MCP, corpus determinist, `B-min` provizoriu | Gate B complet sau Hermes |
| S4 — buclă deterministă | worldgen distribution, B-distribution, runner, actori scriptați, Gate C1 | longitudinalitate calificată |
| S5 — agnosticism | rerulare Gate B pe toate cele trei registry-uri, apoi Gate C2 din același build | acoperire universală de industrii |
| S6 — longitudinal | fault injection și 30–60 zile virtuale, Gate D | AI conversațional calificat |
| S7 — AI/personas | proxy controlat, E1–E3 și corpus statistic | producție |
| S8 — Hermes | F1 cu agent determinist, apoi F2 cu operatorul E înghețat | canal sau pilot de producție |

Substratul remote existent corespunde numai parțial S0: izolarea de rețea,
sursele fixate și resetul sunt utile, dar addon-ul snapshot nu este
implementarea PMORG v2, iar memoria, oracle, runnerul, personas, corpusul și
scorerul nu există încă în acea stivă.

`aipm/` este o bază reutilizabilă pentru memorie — migrări, proveniență,
ancorare, receipts și suite golden — dar nu este oracle și nu este încă
contractul MCP v2. Înainte de S3 are nevoie cel puțin de registry negociat,
instance/company/run namespace, timp valid explicit, contradicție și
supersession structurale, persistența stării conversaționale necesare și
configurația fail-closed descrisă în §3.2. Tabelele truth/split/score nu se
adaugă în schema memoriei.

## 16. Decizii fixate și întrebări rămase

Prin acest document se propun ca decizii, nu ca întrebări:

- oracle este separat fizic și inaccesibil SUT;
- worldgen are nucleu generic și domain packs;
- fiecare profil/run are baze și namespace-uri curate;
- corpusul are train, calibration și hidden-test fără lineage comun;
- runul și verdictul sunt identificate prin manifeste și hash-uri;
- Gate C–D, E1, F1 și F2-E1 folosesc actori scriptați; LLM personas apar în
  E2 și replicile E3 aferente, inclusiv F2-E2/E3;
- resetarea distruge volumele; producția nu furnizează infrastructură de test.

Rămân de stabilit înaintea implementării etapelor corespunzătoare:

1. formatul exact SQL/JSON Schema și limbajul kernelului de evaluare;
2. pragurile și volumele minime per metrică, fixate la calibrare;
3. custodele și procedura de rotație pentru hidden-test;
4. politica de retenție și criptare a artefactelor Gate E/F2;
5. modelul/providerul pentru operator și personas și bugetul per suită;
6. granularitatea domain pack-ului HoReCa, inclusiv POS;
7. criteriul cantitativ de realism înaintea unui pilot;
8. forma exactă a semnăturii verdictului și a registrului de suite.
