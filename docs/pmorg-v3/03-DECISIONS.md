# PMORG v3 — registrul deciziilor

| Câmp | Valoare |
|---|---|
| Status | ADR-301–305, 307–312 și 314–318 Accepted; ADR-306/313 Superseded |
| Versiune | `3.0-baseline.3` |
| Data | 2026-07-19 |

O decizie `Accepted` este normativă pentru v3. ADR-309–314 au fost acceptate
la requirements freeze `RB-1`, cu interpretările din
[requirements baseline](08-REQUIREMENTS-BASELINE.md). ADR-315–316 sunt
corrigendum-ul `RB-1/C1`. ADR-317–318 formează corrigendum-ul `RB-1/C2`,
rezultat din clarificările ownerului privind profilurile Onyx și caracterul
implementation-agnostic al orchestratorului, consemnate în
`docs/correspondence/002*`.

## ADR-301 — V3 este o nouă generație de implementare

**Status:** Accepted (2026-07-18)

**Decizie:** V3 păstrează intenția operatorului organizațional persistent,
dar este tratat ca proiect de implementare nou. V2, SB2 și SB3 rămân
referințe și surse de teste, nu baza incrementală obligatorie.

**Consecințe:** nu rescriem cerința ca să justificăm codul existent și nu
declarăm prototipurile drept implementare v3.

## ADR-302 — PMORG se construiește ca fork guvernat al Onyx

**Status:** Accepted (2026-07-18)

**Decizie:** release-ul Onyx fixat în manifest devine codebase-ul inițial
pentru chat, UI, agenți, knowledge, RAG, model routing și actions. PMORG este
nucleu first-class al produsului rezultat, nu plugin opțional. Proveniența CE
sau EE a unei capabilități este declarată prin profilul de livrare.

**Consecințe:** pipeline-ul conversațional PMORG nu poate fi ocolit prin
endpointuri generice Onyx. Fork-ul are nevoie de politică upstream și
calificare continuă.

## ADR-303 — Odoo-first rămâne invariantă

**Status:** Accepted (carried forward, 2026-07-18)

**Decizie:** Odoo este ancora ontologică, registrul muncii organizaționale și
sursa stării formale curente. PMORG nu devine ERP-agnostic în prima versiune.

**Consecințe:** „PMORG este o aplicație Odoo” din v2 este superseded ca formă
de produs, dar Odoo-first nu este superseded.

## ADR-304 — Closed world-ul este publicat de Odoo

**Status:** Accepted (carried forward, 2026-07-18)

**Decizie:** universul operațional este intersecția modulelor instalate și
configurate, anchor packs compatibile și aprobate, ACL-urilor, companiei și
politicilor. Evidence poate folosi vocabular liber; efectele și ancorele nu.

**Consecințe:** un tip absent sau un fingerprint incompatibil este refuzat
fail-closed. LLM-ul poate propune o mapare, dar nu publică registry-ul.

## ADR-305 — Semantic Core este parte din produs, cu ownership propriu

**Status:** Accepted (2026-07-18)

**Decizie:** Semantic Core este bounded context obligatoriu în fork-ul
Onyx-PMORG. Memoria organizațională nu este memoria personală, transcriptul
sau indexul Onyx. Semantic Core își păstrează schema și lifecycle-ul; MCP
rămâne contract extern, nu singura cale internă.

**Consecințe:** indexurile sunt proiecții reconstruibile. Evidence, claims,
validările și istoria semantică nu depind de recrearea indexului.

## ADR-306 — Hermes orchestrează, Onyx-PMORG execută pași cognitivi (superseded)

**Status:** Superseded de ADR-318 (2026-07-19); păstrat pentru istoric

**Decizie:** Hermes rămâne orchestratorul persistent vizat. El apelează un
contract `execute_cognitive_step`; nu devine sursa canonică a taskurilor,
termenelor sau memoriei. Un runner determinist validează contractele înaintea
integrării Hermes.

**Consecințe:** agentic execution și longitudinal orchestration sunt
responsabilități distincte. Înlocuirea runnerului cu Hermes nu schimbă Odoo
sau Semantic Core.

## ADR-307 — `project.task` este registrul canonic al muncii

**Status:** Accepted (carried forward, 2026-07-18)

**Decizie:** taskurile umane, agentice, hibride, de clarificare, monitorizare
și escaladare sunt `project.task` extins atunci când au semnificație
organizațională. Kanbanul Hermes nu este un al doilea registru.

**Consecințe:** Onyx-PMORG poate prezenta o proiecție proprie, dar nu creează
split brain. Micro-pașii tehnici rămân runs/events.

## ADR-308 — Zero teste în producție

**Status:** Accepted (carried forward, 2026-07-18)

**Decizie:** orice test, benchmark, calificare și pilot rulează în medii
separate, cu date, persoane, canale și credențiale sintetice/dedicate.

**Consecințe:** un pilot este explicit non-production. Niciun gate nu poate
fi trecut pe date ori infrastructură de producție.

## ADR-309 — Turn Coordinator este unica intrare oficială

**Status:** Accepted (2026-07-18)

**Decizie:** mesajele din Onyx UI și Communication Gateway intră prin același
Turn Coordinator: verificare context, poartă de intimitate înaintea stocării,
evidence capture, recall, cognitive execution, tool preflight, semantic
validation și receipts. Gateway/UI trimit raw content numai în Turn Admission;
Hermes/runnerul și runtime-ul primesc după acceptare doar `AdmittedMessage`
fără content/ref/hash. Un refuz nu traversează orchestratorul persistent.

**Motiv:** pașii de siguranță nu trebuie să depindă de alegerea modelului de
a apela un tool.

## ADR-310 — Datele autoritare au baze și migrații separate

**Status:** Accepted (2026-07-18)

**Decizie:** Odoo, Onyx application DB și Semantic Ledger folosesc baze și
roluri separate. Semantic Core are migrații și backup independente; nu are
foreign keys cross-database. Search/vector store este derivat.

**Motiv:** separă lifecycle-urile, reduce blast radius și permite
reconstrucția indexului fără risc pentru ledger.

## ADR-311 — Spec/evaluation și implementarea fork-ului folosesc două repo-uri

**Status:** Accepted (2026-07-18)

**Decizie:** repository-ul actual `PMORG` rămâne sursa pentru specificații,
contracte, evaluare și referințele v1/v2. Un repository nou,
`PMORG-Platform`, păstrează istoria fork-ului Onyx și implementarea v3.

**Consecințe:** fiecare build `PMORG-Platform` fixează un `spec_version` și un
commit din repo-ul PMORG. Nu se copiază documente divergente fără manifest.

**Alternativă:** un singur repo rezultat prin combinarea istoriilor; respinsă
pentru `RB-1` deoarece complică upstream tracking-ul și păstrarea referinței.

## ADR-312 — Onyx-PMORG este workspace-ul principal

**Status:** Accepted (2026-07-18)

**Decizie:** utilizatorul poartă conversațiile, guvernează vocabularul și
matching-ul de ancoră permis și vede operator inbox plus digestul de gaps în
UI-ul PMORG bazat pe Onyx. Odoo păstrează UI-ul nativ pentru starea formală,
taskuri și fallback manual. UI-ul nu oferă coadă de adnotare umană pentru
`claim_kind`, owner, termen ori semantica mesajului.

**Motiv:** evită două experiențe cognitive paralele fără să ascundă ERP-ul.

## ADR-313 — Distribuția inițială folosește numai suprafața Onyx CE (superseded)

**Status:** Superseded de ADR-317 (2026-07-19); păstrat pentru istoric

**Decizie:** baseline-ul v3 pornește din Onyx CE și exclude codul/directoarele
Enterprise din build până când există o decizie comercială și juridică
separată. Controalele obligatorii care lipsesc din CE se implementează și se
auditează sau se licențiază explicit înainte de date reale.

**Consecințe:** MVP-ul folosește numai date sintetice și scope-uri uniforme
de acces până când permission-aware retrieval este demonstrat.

## ADR-314 — MVP-ul include longitudinalitatea deterministă

**Status:** Accepted (2026-07-18)

**Decizie:** un simplu happy-path vertical este milestone M0, nu MVP final.
MVP-ul v3 trebuie să demonstreze cu timp virtual restart, tăcere, duplicate,
contradicție, supersession și continuarea aceleiași inițiative.

**Motiv:** persistența este în centrul intentului de produs; nu poate fi
amânată în afara afirmației de MVP.

## ADR-315 — HIL semantic este exclusiv vocabular/ancoră; detectorul golului închide tăcerea

**Status:** Accepted prin
[decizia ownerului `001a`](../correspondence/001a-decizie-owner.md)
(2026-07-18)

**Decizie:** interpretarea mesajelor și claim-urilor este automată:
consemnare-cu-chitanță dacă trece politica, tăcere dacă nu. `under_review` este
eliminat din state machine-ul claim-ului. Omul intervine numai pentru entități
noi recurente, tipuri/pack-uri noi și matching de ancoră ambiguu cu consecință.
Detectorul determinist al golului de proveniență devine componentă v3 și face
vizibile efectele materiale rămase fără cauză consemnată.

Approval-ul unei acțiuni și verificarea umană a unui outcome sunt autoritate
business asupra efectului, nu HIL asupra interpretării claim-ului; nu pot
produce ori modifica verdictul semantic.

**Consecințe:** workspace-ul Onyx separă guvernanța vocabular/ancoră de
claims; nu există adnotare umană pe fluxul de mesaje. `pmorg.provenance.gap`
este stare de control Odoo, iar controllerul determinist D1–D5 se execută în
addon-ul/control-plane-ul PMORG din Odoo. Semantic Core furnizează numai
query-urile și receipts/proveniența prin API-ul său de domeniu, iar UI-ul
expune digestul și rata de acoperire fără a acuza persoane.

## ADR-316 — `pmorg-contracts/1.0` supersedează wire contractele v2 pentru v3

**Status:** Accepted prin corecția ownerului la
[Issue `PMORG-Platform#16`](https://github.com/bmvv1995/PMORG-Platform/issues/16)
(2026-07-18)

**Decizie:** contractele v2 rămân înghețate pentru SB3 și reproducere, dar nu
sunt API alternativ în v3. `pmorg-contracts/1.0` este unicul contract canonic
v3; operațiile, erorile și idempotency se portează prin maparea din
[14-V2-CONTRACT-SUPERSESSION](14-V2-CONTRACT-SUPERSESSION.md).

**Consecințe:** nu există dual-write sau compatibilitate implicită. Adaptorul
de test legacy este izolat; rândurile inbox fără request hash verificabil nu
devin stare autoritativă v3.


## ADR-317 — Suprafața Onyx și modul de utilizare sunt axe independente

**Status:** Accepted prin decizia ownerului (2026-07-19)

**Decizie:** fiecare build declară `onyx_surface: ce|ee` și
`usage_mode: development_test|production`. O capabilitate Onyx existentă se
reutilizează implicit dacă trece contractele PMORG, izolarea, securitatea și
constrângerile comerciale; abaterea cere ADR sau waiver versionat. Codul EE nu
se copiază în module PMORG.

Suprafața `ee` poate fi copiată și modificată pentru dezvoltare și testare în
limitele licenței Onyx Enterprise, fără a declara fals o licență de producție.
Orice utilizare, distribuire ori exploatare `ee + production` este refuzată
fail-closed fără o dovadă validă care leagă entitatea autorizată, numărul/scope-ul
de seats și acordul aplicabil. Patchurile directe asupra Software-ului EE și
drepturile aferente rămân sub termenii Onyx Enterprise; numai modulele PMORG
create independent au ownership PMORG separat.

**Consecințe:** calificarea `ce` rămâne o variantă selectabilă și verifică
absența codului EE, dar nu este critical path pentru Semantic Core, contracte
sau integrarea PMORG în Onyx. `ee + development_test` cere proveniență
completă și o gardă tehnică împotriva producției/distribuirii. Gate A testează
matricea suprafață × mod, iar `ee + production` nu poate trece pe baza unei
promisiuni viitoare de licențiere.

## ADR-318 — Contractul orchestratorului este implementation-agnostic

**Status:** Accepted prin clarificarea ownerului (2026-07-19)

**Decizie:** produsul cere un orchestrator persistent care implementează
contractele PMORG de scheduling, retry, checkpoint și reluare. Hermes este o
implementare candidată și poate fi selectat prin adaptor, dar nu este cerință
normativă. Runnerul determinist implementează același contract în MVP.

**Consecințe:** Odoo și Semantic Core nu depind de API-uri sau Kanban Hermes.
Înlocuirea runnerului cu Hermes ori cu alt orchestrator calificat nu schimbă
ownership-ul, contractele sau starea business canonică.

## Relația cu ADR-urile v2

| ADR v2 | Statut în v3 |
|---|---|
| 001 — PMORG este aplicație Odoo | Superseded de 302–303; Odoo-first rămâne |
| 002 — anchor packs | Reaffirmed de 304 |
| 003 — `project.task` canonic | Reaffirmed de 307 |
| 004 — runtime și memoria externe | Superseded de 305–306; ownership-ul rămâne separat |
| 005 — admitere validată în memorie | Reaffirmed |
| 006 — comenzi agentice controlate | Reaffirmed |
| 007 — longitudinalitate prin stare persistentă | Reaffirmed |
| 008 — Hermes după runner | Superseded de 318; adaptor opțional după runner |
| 009 — MVP real Odoo + memorie | Superseded: v3 include și fork-ul Onyx-PMORG |
| 010 — zero teste în producție | Reaffirmed de 308 |
| 011 — produs unic, addon-uri Odoo | Superseded ca topologie de 302 și 305 |
| 012 — self-hosting LLM | Reaffirmed |
| 013 — organization-agnostic | Reaffirmed |
| 014 — `pmorg.identity` | Reaffirmed și extins cu bindings Onyx/canal |
| 015 — oracle separat | Reaffirmed prin `EVAL-003` |
| 016 — worldgen și domain packs | Reaffirmed pentru MVP |
| 017 — run bundle imuabil | Reaffirmed, adaptat cu versiunile Onyx-PMORG |
| 018 — splituri de corpus | Reaffirmed pentru evaluarea AI ulterioară |
