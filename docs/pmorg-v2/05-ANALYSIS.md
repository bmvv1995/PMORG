# PMORG — analiza cerinței v2, a implementării v1 și a oportunității de business

| Câmp | Valoare |
|---|---|
| Status | Analiză independentă, pentru decizia de aprobare a suitei v2 |
| Versiune | 0.1 |
| Data | 2026-07-16 |
| Domeniu | Cerința `docs/pmorg-v2/`, implementarea curentă (v1), piața |
| Metodă | Audit de cod cu rularea reală a testelor + review adversarial al specificației + cercetare de piață cu surse (iulie 2026) |

## 1. Rezumat executiv

1. **Cerința v2 este o specificație neobișnuit de disciplinată** — invariante
   testabile, failure modes per componentă, ADR-uri cu alternative respinse,
   „zero teste în producție". Slăbiciunea ei centrală: **își ascunde cele mai
   grele probleme în spatele unor substantive nedefinite** („reconciliere",
   `memory_pending`, `execute_authorized_command`) și poartă presupuneri
   neanalizate despre Odoo 19 Community (lipsa modulului Approvals,
   timeline-ul Enterprise-only, licențierea LGPL nediscutată).
2. **v1 este reală și verificată**: suita `aipm` a fost rulată în acest audit
   pe PostgreSQL 16 + pgvector real — **109 teste trec** (111 colectate,
   1 skipped, 1 deselectat). Garanțiile centrale (poartă de scriere
   `message_post`-only, idempotență, post-validarea mecanică a claims,
   identitate structurală, poartă de intimitate) sunt impuse de cod și de
   schemă, nu de prompturi. Conducta de sedimentare e validată pe Telegram
   real. v1 rămâne însă pre-go-live, legată de o instalare de referință.
3. **Gap-ul v1→v2 este mare și inegal: circa 20–25% din v2 există azi.**
   Memoria e singura felie cu reutilizare consistentă (~50%). Centrul de
   greutate al v2 — aplicația Odoo `pmorg_core`, claim/lease/idempotency
   atomic, outbox/inbox, anchor packs, controller-e, runner determinist —
   este la 0%. Propria formulare a arhitecturii e corectă: PMORG actual e
   „bază de componente și prototipuri".
4. **Riscul strategic nr. 1 al tranziției**: ADR-006 renunță la cea mai
   puternică garanție implementată a v1 (o singură scriere Odoo permisă,
   verificată mecanic) în schimbul unei promisiuni încă neimplementate
   (~16 comenzi validate). Până când validarea per comandă nu e la fel de
   mecanică precum frozenset-ul de azi, v2 e o regresie de securitate cu
   narativ de progres.
5. **Oportunitatea de business e reală, dar fereastra se îngustează.**
   Piața agentic AI ~9–15 mld USD în 2026 (CAGR 40%+); nimeni nu combină azi
   (a) ownership longitudinal al inițiativei, (b) închidere doar cu dovezi
   verificate, (c) memorie organizațională ancorată în ERP. Height —
   singurul „autonomous PM" standalone — s-a închis în 2025: golul există,
   dar fără distribuție nu poate fi ocupat. Competitorul de urmărit nr. 1 e
   **Odoo SA însuși** (agentic AI anunțat pentru Odoo 20, H2 2026).
6. **Reglementarea e navigabilă, dar decisivă ca design de produs**: un
   sistem care alocă sarcini și monitorizează execuția angajaților este
   foarte probabil **high-risk sub EU AI Act Annex III 4(b)**; amânarea
   obligațiilor (Digital Omnibus, iunie 2026) dă o fereastră până la
   **2 decembrie 2027**, dar transparența Art. 50 (agentul se declară AI)
   se aplică de la **2 august 2026**. Telegram este veriga slabă GDPR.

## 2. Analiza cerinței v2

### 2.1 Ce definește suita

Cele cinci documente definesc un **operator organizațional persistent**
construit ca aplicație Odoo: Odoo = ontologia executabilă și starea formală;
`project.task` extins = registrul canonic al muncii umane + agentice; runtime
extern (țintă: Hermes) = orchestrare episodică prin controller-e; memoria
externă prin MCP = evidențe, claims, proveniență; canalele = transport
înlocuibil. Longitudinalitatea vine din stare persistentă + operații
idempotente, nu dintr-o sesiune LLM eternă. MVP-ul construiește real Odoo și
memoria, simulează determinist orchestrarea, timpul și canalul, exclusiv pe
date sintetice (gate-urile A–F).

### 2.2 Puncte forte (de păstrat neatinse)

- **Invariantele din 00-PRODUCT** (reconstrucția stării fără transcript,
  formalizarea oricărui efect în Odoo, supersession fără ștergerea istoriei)
  — direct testabile, rare la acest stadiu.
- **Tabelul failure modes (01 §12)** — comportament corect definit pentru
  fiecare componentă indisponibilă, inclusiv crash după efect extern.
- **Fail-closed semantic pe anchor packs** — previne halucinarea ontologiei;
  mapările custom nu se promovează fără om.
- **ADR-010 „zero teste în producție"** cu raționalizările tipice respinse
  explicit; **ADR-urile** cu disciplina Proposed/Accepted/Superseded și
  gardul din 04 §3 (implementarea se oprește pe ADR-uri neaprobate).
- **Onestitate arhitecturală**: „nu se pretinde o tranzacție distribuită" —
  outbox/inbox + compensări + reconciliere, în loc de o promisiune imposibilă.
- **Runnerul determinist ca suită de acceptanță reutilizabilă pentru Hermes**
  (Gate F) — înlocuibilitatea runtime-ului devine test mecanic.
- **Separarea determinist/AI per controller** și fixture-urile negative din
  MVP (hash greșit, validator neautorizat, interdicția auto-validării).

### 2.3 Riscuri de specificație

1. **MVP infrastructură-greu pentru valoarea de învățare produsă**: ~17
   modele, API atomic cu lease/heartbeat/watchdog, trei idempotency-uri
   separate și anchor packs versionate — toate pentru un smoke test cu o
   singură conversație scriptată. Pentru o echipă foarte mică, riscul este
   consumarea bugetului pe schelărie înainte de prima lecție de produs.
2. **Odoo 19 Community — presupuneri neanalizate**: modulul Approvals e
   Enterprise (mașinăria `request_approval`/`approval_required` trebuie
   construită de la zero — nemenționat); vederile timeline/Gantt sunt
   Enterprise-only, iar 02 §4.1 cere „UI minim pentru… timeline"; Odoo 19 e
   cea mai nouă versiune majoră, cu ecosistemul OCA încă în portare. Niciun
   ADR nu justifică versiunea și nu discută postura de licențiere (LGPL-3).
3. **`execute_authorized_command(...)` — ușă din dos generică** într-o
   suprafață altfel îngustă: fără registru de comenzi permise, fără schemă,
   fără exemple. Nespecificat strâns, anulează ADR-006.
4. **Contractul se îngheață înaintea consumatorului** (02 §6):
   `propose_plan_version` și `record_confirmation` nu sunt exersate de
   niciun pas al smoke-ului — se îngheață endpoint-uri fără niciun test de
   consumator.
5. **Validare de fezabilitate, nu de dezirabilitate**: până la Gate E–F totul
   e scriptat și sintetic; riscul că oamenii și LLM-ul real sparg modelul
   conversație/corelare se materializează târziu, când costul schimbării e
   maxim.
6. **Timpul virtual vs ceasul Odoo**: `list_due_work(now)` primește timp
   injectat, dar `create_date`/`write_date` și orice comparație internă Odoo
   folosesc ceasul de perete — simularea a 30–60 de zile cere o disciplină
   nespusă nicăieri, ușor de spart la primul câmp datetime uitat.
7. **Reutilizarea aipm afirmată fără gap analysis** (02 §4.3): ancorele v2
   cer instance UUID, company, schema_version, write_date observat; modelul
   v1 are `(code, res_id)`. Gate B poate exploda în refactorizare majoră
   dacă nu e planificat redesign-ul.
8. **Cascada fail-closed fără plan pentru munca în zbor**: pack dezactivat la
   schimbare de fingerprint — ce se întâmplă cu inițiativele active ale căror
   ancore aparțin pack-ului?

### 2.4 Ambiguități și contradicții interne (verificabile)

- **Suprafața MCP diferă între documente**: 01 §8 are `memory_record_decision`
  / `memory_record_commitment`; suprafața minimă MVP (02 §4.3) nu le are —
  dar calificarea longitudinală (02 §10 pct. 10) cere „supersession al unei
  decizii", imposibil de testat fără calea de înregistrare a deciziei.
- **Reconcilierea manual-vs-claim doar numită** (01 §4.1): cine câștigă când
  un om trage taskul în „Finalizat" sub lease activ? Ce coadă procesează
  „răspunsul necorelat" și cu ce timeout?
- **`memory_pending` fără semantică**: nu există în vocabularul stărilor;
  poate un task să se închidă cât timp dovada lui e `memory_pending`?
  Oricare răspuns încalcă fie „fără închidere fără dovezi", fie promisiunea
  de continuitate.
- **`at_risk`/`blocked`/`paused`/`degraded`**: 00 le folosește în promisiunea
  de business; 01 §3.1 amână decizia (state vs flags vs obiecte); `paused` și
  `degraded` lipsesc din `initiative_state`.
- **Modelul conversației lipsește**: 01 §9 cere ca Odoo să păstreze starea
  conversației, dar tabelul de modele nu conține `pmorg.conversation`.
- **Unde trăiește logica longitudinală în MVP**: 01 §7 pune controller-ele în
  runtime; 02 §4.4 spune „politicile și tranzițiile aparțin Odoo; runnerul nu
  conține reguli de business". Granița exactă e nedecisă.
- **Bootstrap-ul guvernanței**: cine și prin ce act trece ADR-urile în
  `Accepted`, și care sunt cele „necesare" pentru prima felie?
- **Smoke scenario sare peste plan și confirmare**: ciclul cere
  `planned → awaiting_confirmation → active`, dar scenariul (02 §8) trece de
  la obiectiv direct la crearea taskului.
- **Invarianta 4 („nicio acțiune nu se dublează")** e absolută în 00, dar
  pentru efecte externe exactly-once e imposibil; 01 o nuanțează corect —
  documentul de produs promite mai mult decât livrează arhitectura.

### 2.5 Recomandări înainte de aprobarea suitei

1. Specificați la nivel de mașină de stări: **reconcilierea manual-vs-claim**,
   **`memory_pending`** și **registrul închis al `execute_authorized_command`**.
2. Adăugați un **ADR pentru versiunea Odoo** (19 vs 18/17), fluxul de
   aprobare pe Community și **postura de licențiere** a addon-urilor.
3. Definiți o **versiune degradată a DoD** (ce se taie primul sub presiune —
   ex. outbox complet, anchor packs versionate) ca MVP-ul să nu fie monolitic.
4. Aliniați suprafața MCP între 01 §8 și 02 §4.3 (minim: adăugați
   `memory_record_decision` în MVP sau scoateți testul de supersession al
   deciziei din calificare).
5. Faceți un **gap analysis explicit aipm→memoria v2** înainte de a paria
   Gate B pe „reutilizare și extindere".
6. Portați explicit din moștenire apărările câștigate scump și absente ca
   cerințe distincte în v2: **autoritatea din metadate, nu din conținut**
   (anti-injecție prin memorie), **pauza de urgență** ca obiect de prim rang,
   **plafonul de cost LLM**.

## 3. Auditul implementării v1

### 3.1 `aipm` — memoria (verificat prin rulare)

~5.300 LOC Python + ~890 SQL. **Suita a fost rulată real în acest audit**
(PostgreSQL 16 + pgvector, bază efemeră migrată prin chiar runner-ul de
migrări): **111 colectate → 109 passed, 1 skipped, 1 deselectat (~15s)** —
confirmă cifra din README. Garanțiile sunt în cod și în schemă, nu declarative:

- **Poarta de scriere**: `WRITE_ALLOWLIST = frozenset({"message_post"})`
  (`adapter/contract.py:12`), verificată în calea unică `_execute` a ambelor
  adaptoare, înainte de transport.
- **Idempotență**: `ingest_log(source_type, source_ref)` + index unic parțial
  pe `content_hash` + advisory lock per `memory_id` pe chitanțe + recuperare
  fetch-and-compare contra dublei postări.
- **Anti-halucinare pe două fronturi**: la rezoluție se acceptă doar id-uri
  din lista reală de candidați; la recall, claims-urile sunt post-validate
  mecanic contra mulțimii S citite live din Odoo — fapt doar ce există acum;
  suport doar-memorie → forțat „ipoteză"; testat inclusiv cu valori fabricate
  de LLM.
- **Identitate structurală**: `identity_map` scris doar prin migrare; autor
  nemapat = gol de cunoaștere înregistrat, niciodată identitate inventată.
- **Poarta de intimitate**: denylist deterministă (pliere diacritice + prefix
  de cuvânt pentru flexiuni RO), aplicată sincron înainte de persistare pe
  conducta gateway; refuz consemnat fără conținut.
- **Guvernanța schemei**: migrări forward-only cu verificare de hash; trigger
  PG pentru matricea kind×subject; `chat_turn` append-only prin trigger.

Limitări reale: poarta de intimitate acoperă **doar conducta gateway** (nu
`/api/chat`, nu chatterul); sesiuni de chat in-memory; **zero teste de
integrare contra unui Odoo real** (semantica fake=real e o presupunere);
auth cu comparație non-constant-time atenuată de bind pe localhost;
o discrepanță declarat-vs-implementat: `INGEST_ENABLED` are default `True`
în `config.py:56` („compat cu deploy-ul existent"), deși doctrina cere
aterizare inertă — installer-ul o setează explicit pe `false`, dar default-ul
codului contrazice legea.

**Maturitate: funcțional spre production-intent pentru un deploy
single-tenant self-hosted; nu „production-hardened" generic.**

### 3.2 Componentele de proces (`components/`, ~2.000 LOC)

- **hermes-ops-mcp** (539 LOC, zero dependențe): ~24 unelte deterministe
  (kanban cu gări, admin-queue, 3 citiri aipm îngrădite prin frozenset
  `READ_ENDPOINTS`). Identitatea vine din env (`HERMES_OPS_AUTHOR`) — PM-ul
  nu poate semna drept altcineva. Regula ARTEFACT e structurală
  (`kanban_complete` refuză fără `result`). Piesa cea mai matură.
- **Îngrădirea PM-ului e fizică, pe trei straturi**: `settings.json` cu deny
  pe Bash/Write/Edit/NotebookEdit/WebFetch/WebSearch/Task și allow doar
  `mcp__hermes-ops`; suprafața MCP fixă la deploy (extindere = commit git);
  execuția admin scoasă din agent. **Gaură reală**: deny-list-ul nu acoperă
  Read/Glob/Grep — „doar MCP" nu e literal adevărat (PM-ul poate citi
  fișiere accesibile din workdir).
- **Ritual de aprobare** în 4 trepte (cerere motivată → Telegram → pagină
  doar-localhost cu token → retastarea exactă a numelui acțiunii), execuție
  deterministă + commit git. **Vector de injecție confirmat**:
  `ontology_install` construiește `bash -c` prin f-string cu `p["profile"]`
  nesanitizat (`cc-mirror-shim:257–259`), iar `soul_write` face
  `os.path.join` cu același parametru (traversare posibilă) — atenuat de
  ritual, dar executorul „determinist" are o cale de escaladare dinspre agent.
- **cc-bridge / cc-mirror-shim** (~1.100 LOC): puntea Hermes↔Claude Code prin
  tmux — starea din hooks (nu scraping), dar injecția de text, aprobările și
  AskUserQuestion depind de scraping-ul TUI — **contract nedocumentat, se
  rupe la orice update de UI**. Fără niciun test. Port 9127 fără
  autentificare (model de încredere „un singur utilizator pe server").
- **Snapshot vs sursă vie**: căi `/home/vscode` și emailul ownerului
  hardcodate, README desincronizat (spune 19 unelte, sunt ~24), dependență de
  un al patrulea repo (`hermes-ontology`) absent din `components/`.

### 3.3 Integrarea (etapele 1–10) și validarea reală

Toate cele 10 etape din PLAN-INTEGRARE sunt implementate (2026-07-08/09),
fiecare cu criteriu de ieșire scris înaintea implementării și test numit.
Lanțul critic **Telegram → gateway → vamă de identitate → poartă de
intimitate → memorie** e validat pe Telegram real (2026-07-09): termen
interzis flexionat → `privacy_blocked` fără urme; mesaj curat → `accepted`
cu identitatea reală. **Nevalidat pe viu**: veriga finală (fapt memorat cu
LLM real — cere `LLM_API_KEY`); extracția e dovedită doar cu FakeLLM.

Rămase deliberat: crearea `project.project` în Odoo la crearea board-ului;
bucla de contestare a chitanțelor (D4); trunchierea hook-ului la 500 de
caractere. Datorii operaționale recunoscute și nerezolvate: **plafon de cost
LLM inexistent**, secrete în clar fără rotație, provizionarea Odoo
neverificată de installer, reîmprospătarea instantaneelor `components/`.

### 3.4 Concluzia auditului v1

v1 este un prototip disciplinat și onest documentat, cu un nucleu de memorie
solid și verificat, un strat de proces funcțional dar fragil (tmux-scraping,
fără teste pe punte) și o singură instalare de referință. Nu a rulat
niciodată cap-coadă cu Odoo real + LLM real + client real.

## 4. Gap v1 → v2

### 4.1 Reutilizabil direct (activele care plătesc dividende)

| Activ v1 | Rol în v2 | Notă |
|---|---|---|
| Nucleul aipm (pipeline, idempotență, dedup, chitanțe; 109 teste) | Substanța serviciului de memorie (ADR-005) | ~50% din memoria v2 există; contractul MCP și validarea (autoritate, contradicții, supersession, timeline) se construiesc deasupra |
| Post-validarea mecanică a claims (mulțimea S) | Condiția de acceptare 5 din arhitectură | Cea mai valoroasă piesă v1: exact invariantul central al memoriei, deja impus de cod |
| identity_map + privacy.py + hook aipm-sediment | Contractul de canal §9 („identitatea vine structural din adaptor") | De generalizat de la Telegram la send/receive cu correlation |
| Infrastructura de test (Fake-uri first-class, DB efemeră, injecție de defecte, suite cu porți) | Know-how pentru runnerul determinist și Gate E | Nu e runnerul cerut (lipsesc timpul virtual, canalul simulat), dar e exact disciplina cerută |
| Adaptorul XML-RPC cu gate-before-transport | Citirea live a ancorelor; șablon pentru comenzile înguste | Validat doar contra fake-ului — datorie critică în v2 |
| hermes-ops-mcp | Șablon pentru adaptorul MCP al memoriei și stratul `kanban_*`→API PMORG | Se reutilizează pattern-ul, nu suprafața |
| Rapoarte cu excludere live + digest idempotent | Precursorii părții deterministe a controller-elor Deadline/Commitment | Lipsesc bucla cu `next_check_at` și efectul formal |
| Installere idempotente, aterizare inertă, backup | Operarea memoriei în mediile de test | Addon-ul Odoo are propriul mecanism |

### 4.2 Acoperit parțial (ce lipsește concret)

Memoria validată (fără separarea evidență/claim, autoritate, contradicții
first-class, valabilitate temporală, supersession, timeline); suprafața MCP
(3 unelte read-only vs ~9 `memory_*`); anchor packs (inventar închis de 9
tipuri vs pachete YAML cu discovery, fingerprint și fail-closed; ancora v1 nu
are instance UUID / company / schema_version); idempotența (dovedită pe
conducta memoriei, dar fără `idempotency_key` per comandă, `expected_version`,
outbox tranzacțional); controller-ele (rapoarte există, bucla cu stare
persistentă nu); verificarea rezultatelor (regula ARTEFACT verifică prezența,
nu substanța/autoritatea); politicile de autonomie (îngrădire binară fizică
vs 5 niveluri per acțiune/model/companie); failure modes (fără circuit
breaker, `memory_pending`, watchdog de lease-uri, reconciliere).

### 4.3 Complet lipsă (centrul de greutate al v2)

**Zero cod** pentru: aplicația Odoo `pmorg_core` (niciun `odoo_addons/` în
repo — verificat) cu toate cele ~17 modele; extensia `project.task` și UI-ul
Odoo; claim/lease/idempotency atomic server-side; outbox/inbox tranzacțional
cu plicul standard; API-ul de orchestrare (~16 comenzi); contractul MCP
formal versionat; runnerul determinist cu timp virtual și canal simulat;
mașina duală de stări; ciclul inițiativei (conceptul de *inițiativă* nu
există nicăieri în v1 — v1 e centrat pe task și memorie); fixtures sintetice
Delta Distribution + gate-urile A–F; mediul Odoo 19 de test (v1 nu a rulat
niciodată contra unui Odoo real).

### 4.4 Estimare de efort (calitativ, până la Gate C, apoi F)

1. **Schelet Odoo (Gate A)** — construcție nouă 100%, dar cea mai bine
   specificată felie; efort MEDIU, dominat de ridicarea mediului Odoo 19 de
   test, neexersat vreodată în proiect (~1–2 săptămâni-om echivalente).
2. **Contracte (claim/lease, outbox/inbox, ~16 comenzi, mașina duală,
   autonomie)** — **felia cea mai grea**: zero cod reutilizabil, design
   distribuit subtil, blocantă pentru tot; efort MARE (~2–3× scheletul).
3. **Memorie MCP (Gate B)** — singura felie cu reutilizare masivă (~50%);
   efort MEDIU-MARE, cu plasa de siguranță a suitei de teste v1.
4. **Runner + canal simulat + timp virtual (Gate C)** — construcție nouă cu
   know-how transferabil; efort MEDIU.
5. **Gate D** — scenaristică pe infrastructura C, MEDIU; **Gate E** — MIC
   (cultura „LLM-ul nu poate ocoli validările" e deja exersată); **Gate F
   (Hermes)** — MEDIU-MARE cu incertitudine maximă: puntea tmux actuală
   probabil nu demonstrează claim atomic + observabilitate fără rework
   serios.

### 4.5 Riscurile tranziției

1. **Regresie de securitate mascată ca progres** (ADR-006) — vezi rezumatul.
   Mitigare: fiecare comandă nouă primește gate mecanic + test negativ
   înainte de a fi expusă; poarta veche rămâne pentru memoria migrată.
2. **Split brain**: boardul viu de pe serverul de referință vs construcția
   v2; cutover-ul cu legacy IDs e un pas one-shot fără repetiție.
3. **Odoo 19 nevalidat**: presupuneri acumulate în FakeOdooAdapter pot pica
   la primul contact real; schema Odoo se mișcă între versiuni.
4. **Gate F pe cc-bridge** (scraping tmux, fără teste, vector de injecție în
   executorul admin) — costul respingerii târzii a Hermes e real; ADR-008 îl
   izolează corect.
5. **Toate ADR-urile sunt `Proposed`** — blocaj de proces sau implementare
   „ca și cum", exact anti-pattern-ul interzis de documente.
6. **Tipar recurent din moștenire**: C7 a rămas pe hârtie în linia de proces;
   supersession/valabilitatea temporală riscă același destin dacă nucleul
   aipm e portat fără mecanismele noi.
7. **Datoriile operaționale moștenite** (plafon LLM, secrete, provizionare
   Odoo) reapar nealterate la Gate E și la pilot.

## 5. Oportunitatea de business

*Cercetare web efectuată la 2026-07-16; sursele-cheie sunt citate inline.
Cifrele de piață sunt estimări ale unor firme de research cu metodologii
diferite — folosite aici ca ordine de mărime, nu ca adevăruri contabile.*

### 5.1 Piața și momentul

- **Agentic AI**: ~9–15 mld USD în 2026, consens pe CAGR 40%+ (Mordor:
  9,89 mld → 57,4 mld până în 2031; Fortune BI, Precedence converg).
- **AI în project management**: ~4,2 mld USD în 2026 → ~14,4 mld până în
  2034 (Precedence; CAGR ~17%).
- **Analiștii susțin teza produsului**: Gartner — 80% din sarcinile de PM
  eliminate de AI până în 2030 (predicția din 2019); 40% din aplicațiile
  enterprise cu agenți task-specific până la finalul lui 2026 (de la <5% în
  2025); 15% din deciziile de lucru zilnice autonome până în 2028. Forrester
  2026: software-ul enterprise trece la „găzduirea unei forțe de muncă
  digitale"; 30% din vendori lansează servere MCP.
- **Contrapunctul critic**: doar 23% din organizații scalează agentic AI
  undeva (McKinsey, nicio funcție >10%); **Gartner: >40% din proiectele
  agentice anulate până în 2027** — execuția, nu cererea, e riscul
  categoriei. Încrederea în agenți complet autonomi **scade** (43%→27%
  într-un an, McKinsey) — human-in-the-loop e cerință comercială, nu doar
  legală. Doctrina v1/v2 (AI propune, omul decide, dovezi la închidere) e
  deci exact pe direcția cererii, nu împotriva ei.
- **IMM-urile** (ținta PMORG): 61% folosesc activ AI + 29% experimentează
  (Pax8, Q2 2026), dar doar ~14% îl au integrat în operațiunile de bază
  (Goldman Sachs); barierele declarate — lipsa expertizei (28%), cost/ROI
  (24%), securitate (21%) — sunt exact ce rezolvă un operator „la cheie",
  self-hosted, cu guvernanță mecanică.
- **Categoria „AI employee" e finanțată agresiv**: Cognition/Devin evaluat
  26 mld USD (mai 2026), Sierra 15 mld USD cu pricing per-outcome, plus 11x,
  Ema, Artisan. Nimeni nu ocupă încă nișa „operator organizațional persistent
  pentru IMM-uri, nativ în ERP".

### 5.2 Competiția și golul de piață

Starea la iulie 2026, pe trei familii:

1. **Unelte PM cu agenți**: ClickUp Super Agents ($28/user/lună „Everything
   AI") și Wrike AI Agents (lansați feb. 2026) — cele mai avansate pe
   execuție autonomă multi-pas; Monday „digital workers" pe credite
   (~$1,50/acțiune complexă); Asana AI Teammates în GA (~21 agenți); Motion
   se vinde direct ca „AI project manager". Toate rămân ancorate în datele
   propriului tool și **niciunul nu are model public de „proof-of-done"** —
   închiderea rămâne „omul a bifat".
2. **Platforme de agenți** (Lindy $50–200/lună, Relevance, Dust, CrewAI,
   Microsoft Planner Agent — GA iunie 2026): cărămizile, nu casa —
   persistență per-trigger, fără ontologie de proiect, fără verificare de
   rezultat, fără ERP.
3. **Odoo însuși — competitorul de urmărit nr. 1**: Odoo 19 (oct. 2025) a
   adus „Odoo AI" — agenți conversaționali cu RAG, completare de câmpuri,
   din 19.3 agenți care creează/actualizează înregistrări. **Dar documentația
   oficială 19.0 arată agenți strict reactivi**: fără scheduling autonom,
   fără follow-up auto-inițiat, fără memorie longitudinală. AI-ul e
   Enterprise-only (~$24,90/user/lună + credite IAP). Odoo 20 (anunțat
   H2 2026) promite „agentic AI" multi-pas — fereastra pe execuția punctuală
   se poate închide în 12–24 luni. În appstore/OCA: aproape numai conectori
   LLM și gateway-uri MCP; **niciun „operator PM persistent" matur — golul e
   deschis**.

**Lecția Height**: singurul produs poziționat explicit „autonomous project
management" s-a închis în septembrie 2025 — nișa există, dar un tool
standalone fără distribuție nu o poate ocupa. PMORG evită exact acest mod de
eșec prin strategia Odoo-first (distribuție prin ecosistem, nu tool nou).

**Golul PMORG** = intersecția a trei proprietăți pe care nimeni nu le
combină: (a) ownership longitudinal al inițiativei (urmărire pe săptămâni,
follow-up pe tăcere, escaladare); (b) închidere doar după verificarea
rezultatului cu dovezi; (c) memorie organizațională ancorată în ERP ca sursă
de adevăr. Cerința v2 este, aproape punct cu punct, specificația acestui gol.

### 5.3 Ecosistemul Odoo ca teren de lansare

- **Scara**: Odoo revendică ~28M utilizatori (surse independente: 13–16M,
  170k+ companii), 7–13k clienți noi/lună, ~650M EUR facturați în 2025
  (ARR +40–46%), evaluare ~7 mld EUR. Clientul tipic: 20–249 angajați —
  exact segmentul PMORG.
- **Canalul există**: App Store cu 40–50k aplicații, dezvoltatorul păstrează
  70%; bestselleruri la ~$600 cu mii de descărcări. Dar modulele terțe cu
  Python **nu rulează pe Odoo Online** — doar Odoo.sh/on-premise, ceea ce
  împinge natural spre self-hosting și **se aliniază cu povestea de
  suveranitate a datelor** (driver real de cumpărare în UE post-CLOUD Act).
- **România/ECE**: 22 parteneri oficiali RO (1 Gold, 6 Silver), localizare
  fiscală ținută de comunitate (OCA/l10n-romania), fonduri UE de digitalizare
  folosite ca vector de vânzare Odoo — cerere reală, concurență locală mică.
- **Riscul de sherlocking are istoric documentat**: pivotul open-core 2015;
  WhatsApp nativ în v17 peste o nișă de conectori bestseller; Helpdesk,
  Rental, Knowledge, Sign absorbite rând pe rând; v19 cu 50+ verticale și AI
  nativ. Tiparul: funcționalitatea orizontală populară ajunge în core în 1–3
  versiuni. Apărarea PMORG: profunzime verticală de proces (bucla
  inițiativă→dovadă→închidere), nu „AI în Odoo" generic; mix
  licență + servicii + mentenanță, nu vânzare one-off.

### 5.4 Reglementare: decisivă ca design de produs

- **EU AI Act**: un sistem care **alocă sarcini pe baza comportamentului
  angajaților sau le monitorizează performanța este high-risk**
  (Annex III 4(b)). Un PMORG care distribuie autonom taskuri și urmărește
  execuția intră foarte probabil în categorie; un design în care **agentul
  sugerează și omul decide** poate ieși prin excepția Art. 6(3) — aceasta e
  decizia de produs cu cea mai mare miză juridică, și încă un argument
  pentru nivelurile `recommend`/`approval_required` din ADR-006.
- **Fereastra**: Digital Omnibus (iunie 2026) amână obligațiile high-risk de
  la 2 aug. 2026 la **2 dec. 2027** (~17 luni pentru construirea
  conformității: supraveghere umană, loguri, informarea angajaților). **NU
  se amână**: transparența Art. 50 — agentul trebuie să se declare AI când
  scrie oamenilor — de la **2 aug. 2026** (de implementat în orice pilot).
- **GDPR**: consimțământul angajaților e invalid ca bază legală (dezechilibru
  de putere, poziție constantă EDPB) → interes legitim + balancing test +
  DPIA; în DE/FR/BE/NL, consultarea works council înainte de deploy.
  Arhitectura v1/v2 (poartă de intimitate, listă „niciodată la AI",
  minimizare, self-hosted) e un avantaj de conformitate vandabil — moștenirea
  a anticipat corect aceste cerințe.
- **Telegram e veriga slabă**: fără DPA, sediu Dubai, fără E2E implicit —
  nepotrivit pentru medii reglementate. Recomandare de produs: canale de
  lucru dedicate/controlabile ca primă clasă (Odoo Discuss, e-mail,
  Teams/Slack cu DPA), Telegram doar ca opțiune asumată de client.
- Notă: intuițiile juridice din analiza externă v0.2 (moștenire) s-au
  confirmat aproape integral — inclusiv fereastra până la dec. 2027 — dar
  opinia juridică formală rămâne datorie deschisă înainte de date reale.

### 5.5 Pricing și go-to-market

- **Două ancore de preț** între care trebuie poziționat produsul: software de
  coordonare per seat (ClickUp $7–12, Monday $9–19, Asana $11–25, Motion
  $19–29, Odoo însuși ~$25/user/lună) vs „angajați digitali" la preț de
  salariu (11x ~$36–60k/an, Artisan $1,5–3k/lună, Intercom Fin
  $0,99/rezoluție — referința per-outcome, validată și de acordul Salesforce
  de a cumpăra Fin cu ~3,6 mld USD, iunie 2026, de confirmat la închidere).
- **Willingness-to-pay IMM**: premium de ~10% peste aplicațiile existente
  (SMB Group) pentru AI încorporat; multe firme mici cheltuie deja >$10k/an
  pe AI în total. Concluzie: **nu se vinde la preț 11x către IMM-uri**.
- **Poziționarea realistă**: abonament fix per companie, orientativ
  **200–800 EUR/lună** („o fracțiune dintr-un coordonator part-time"),
  eventual cu componentă măsurabilă de outcome (inițiative închise cu dovezi
  — exact ce PMORG poate măsura mecanic și competitorii nu). De evitat
  per-seat-ul pur: contrazice promisiunea că agentul reduce nevoia de seats.
- **Canalul**: partner-led prin ecosistemul Odoo (partenerii câștigă din
  implementare/configurare — exact ce cere un operator adaptat pe procesele
  clientului); App Store ca vitrină și lead-gen, nu ca venit principal;
  vânzare directă doar pe o nișă verticală cu ROI demonstrabil (moștenirea
  indica HoReCa — instanța de referință există deja).

### 5.6 Verdict de business

**Oportunitatea e reală, diferențiabilă și cu fereastră de timp.** Teza
produsului (operator persistent + dovezi la închidere + memorie ancorată în
ERP) atacă un gol pe care niciun jucător nu-l acoperă și pe care analiștii și
capitalul îl validează ca direcție. Avantajele aparabile sunt exact cele din
arhitectură: bucla completă de accountability (proof-of-done), memoria
organizațională cu proveniență, self-hosting-ul + conformitatea „în cutie"
pentru UE, și distribuția prin ecosistemul Odoo pe segmentul 20–249 angajați.

Condițiile de reușită, în ordine: (1) **viteză** — fereastra față de Odoo 20
și de agenții PM ai incumbenților e de ~12–24 luni; MVP-ul infrastructură-greu
trebuie tăiat pe felia care demonstrează diferențiatorul (bucla
inițiativă→dovadă→închidere), nu pe toată schelăria; (2) **încredere ca
feature** — guvernanța mecanică (autonomie pe niveluri, dovezi, audit) e
argumentul de vânzare central într-o piață în care încrederea în agenți
scade și 40% din proiecte se anulează; (3) **design AI-Act-aware** de la
început (recommend-by-default, Art. 50, DPIA-ready), transformând
reglementarea din obstacol în argument pe care partenerii Odoo îl pot
revinde; (4) **canal înainte de produs complet** — un design partner real
(instanța HoReCa) + 2–3 parteneri Odoo ca early channel, înaintea oricărei
generalizări.

## 6. Recomandări consolidate (prioritizate)

1. **Nu aprobați suita v2 ca atare** — cereți întâi închiderea celor 4
   lacune de specificație: reconcilierea manual-vs-claim, `memory_pending`,
   registrul `execute_authorized_command`, alinierea suprafeței MCP (§2.5).
2. **Adăugați ADR-uri pentru**: versiunea Odoo + fluxul de aprobare pe
   Community + licențiere; pauza de urgență ca cerință de prim rang;
   plafonul de cost LLM; autoritatea din metadate (anti-injecție prin
   memorie) ca invariantă explicită v2.
3. **Regula de aur a tranziției**: nicio comandă de scriere nouă fără gate
   mecanic + test negativ echivalent cu frozenset-ul actual. ADR-006 se
   implementează incremental, comandă cu comandă, nu ca suprafață întreagă.
4. **Gap analysis formal aipm→memoria v2 înainte de Gate B** (schema
   ancorelor, evidență/claim, supersession) — altfel „reutilizarea" e un
   pariu, nu un plan.
5. **Definiți DoD-ul degradat al MVP-ului** (ce se taie primul) și mutați
   diferențiatorul de business (închiderea cu dovezi) cât mai devreme în
   smoke test — el e și demo-ul de vânzare.
6. **Decideți devreme postura AI Act**: `recommend`-by-default cu
   `execute_delegated` opt-in per client poate ține produsul în afara
   high-risk (Art. 6(3)) — cu opinie juridică formală înainte de orice date
   reale.
7. **Planificați înlocuirea/întărirea cc-bridge înainte de Gate F** — puntea
   tmux e cel mai probabil punct de eșec al calificării Hermes; sanitizați
   imediat `ontology_install`/`soul_write` și extindeți deny-list-ul PM cu
   Read/Glob/Grep sau documentați explicit de ce nu.
8. **Corectați discrepanța `INGEST_ENABLED=True`** (default-ul contrazice
   aterizarea inertă) — o linie de cod, dar e litera legii produsului.
9. **De-Telegram-izați povestea de conformitate**: contractul de canal v2 e
   deja agnostic — faceți din canalul „cu DPA" opțiunea implicită a
   pilotului, Telegram opțiune asumată.
10. **Păstrați disciplina care e deja marca proiectului** (criterii de ieșire
    scrise înainte, analize adversariale, instantanee datate, onestitate
    Lege-vs-Obiectiv) — în piața descrisă la §5, ea nu e doar metodă de
    lucru, ci diferențiatorul de încredere care se vinde.

## 7. Anexă — metodologie

Analiza a fost produsă prin: (a) lectura integrală a suitei
`docs/pmorg-v2/`, README, INTENT-UNIFICARE, PLAN-INTEGRARE, GO-LIVE;
(b) audit de cod pe `aipm/` și `components/` cu **rularea reală a suitei de
teste** (PostgreSQL 16 + pgvector provizionat local: 109 passed);
(c) review adversarial independent al specificației v2; (d) analiza
documentelor de moștenire (`docs/aipm/`, `docs/mostenire-pm-organizational/`);
(e) cercetare web la 2026-07-16 pe patru direcții (piață, competiție,
ecosistem Odoo, pricing/reglementare), cu URL-uri păstrate în constatări;
afirmațiile tehnice-cheie despre v1 au fost verificate direct în cod
(`adapter/contract.py:12`, `config.py:56`, `templates/pm-workdir/settings.json`,
`cc-mirror-shim:252–259`). Cifrele de piață provin din surse secundare cu
metodologii diferite și trebuie tratate ca ordine de mărime.
