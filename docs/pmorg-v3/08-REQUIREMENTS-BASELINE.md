# PMORG v3 — requirements baseline

| Câmp | Valoare |
|---|---|
| Status | Accepted |
| Baseline | `RB-1` |
| Versiune produs | `3.0-baseline.1` |
| Data acceptării | 2026-07-18 |
| Scope | MVP structural și longitudinal, Gates A–F |

## 1. Scopul baseline-ului

Acest document îngheață cerința PMORG v3 suficient pentru proiectare tehnică,
estimare și implementare fără reinterpretarea intenției produsului.

Baseline-ul nu fixează încă tagul Onyx, revizia Odoo, providerul LLM sau
configurația Hermes. Acestea sunt selecții de implementare/calificare care se
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

O schimbare de fond după `RB-1` cere ADR nou, impact asupra cerințelor/testelor
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
| `ODO-008` | Onyx, Hermes și modelele SHALL NOT primi acces ORM, SQL sau credential de DB Odoo generic. |
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

## 7. Cerințe de interacțiune și orchestrare

| ID | Cerință obligatorie |
|---|---|
| `INT-001` | Fiecare turn oficial SHALL trece prin Turn Coordinator. |
| `INT-002` | UI-ul PMORG și calea Gateway → Hermes/runner SHALL ajunge în același Turn API și aceeași politică. |
| `INT-003` | Identitatea expeditorului SHALL proveni structural din binding; SHALL NOT fi ghicită din text. |
| `INT-004` | Mesajul SHALL fi capturat durabil ca evidence înainte de execuția cognitivă care îl interpretează. |
| `INT-005` | Fiecare action SHALL avea preflight determinist și receipt. |
| `ORC-001` | Hermes SHALL fi orchestratorul țintă; runnerul determinist SHALL demonstra același contract în MVP. |
| `ORC-002` | Hermes SHALL apela `execute_cognitive_step`; SHALL NOT folosi chat generic drept contract longitudinal. |
| `ORC-003` | O execuție cognitivă SHALL fi bounded, versionată și idempotentă. |
| `ORC-004` | Scheduling, retry și checkpoint Hermes SHALL NOT deveni starea business canonică. |
| `ORC-005` | Controller-ele SHALL executa cel mult un pas idempotent și SHALL persista următoarea verificare. |

## 8. Cerințe de platformă și securitate

| ID | Cerință obligatorie |
|---|---|
| `PLT-001` | PMORG v3 SHALL fi construit ca fork guvernat al Onyx CE, cu baseline tag + SHA exact. |
| `PLT-002` | Semantic Core SHALL fi bounded context first-class, cu ownership și migrații proprii. |
| `PLT-003` | Odoo DB, Onyx DB și Semantic Ledger SHALL folosi baze și roluri distincte; Odoo SHALL NOT scana DB-urile PMORG. |
| `PLT-004` | Codul PMORG de domeniu SHALL fi separat de codul upstream, iar patchurile upstream SHALL fi inventariate. |
| `PLT-005` | Buildul CE al MVP-ului SHALL exclude codul din directoarele Onyx `ee`. |
| `SEC-001` | Fiecare operație SHALL avea `organization_id`, instanță Odoo, companie, identitate și registry fingerprint. |
| `SEC-002` | Accesul cross-organization și cross-company SHALL fi refuzat înainte de retrieval sau action. |
| `SEC-003` | Secretele SHALL NOT apărea în evidence, prompturi, logs ori receipts. |
| `SEC-004` | Prompt injection SHALL NOT activa un tool, anchor type sau nivel de autonomie nepermis. |
| `SEC-005` | Memoria personală Onyx SHALL fi dezactivată pentru agenții PMORG în MVP. |

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
- Gates A–F din [MVP](04-MVP.md).

MVP-ul exclude:

- Hermes real;
- model stochastic drept condiție de PASS;
- canal real;
- date reale;
- multi-tenant la scară;
- fine-tuning, pilot și producție.

Aceste excluderi nu elimină responsabilitățile produsului. Ele amână numai
implementarea concretă la Gate G, H sau I.

## 11. Deciziile înghețate în RB-1

ADR-309–314 sunt acceptate cu următoarea interpretare:

- Turn Coordinator este obligatoriu;
- bazele și rolurile autoritare sunt separate;
- `PMORG` și `PMORG-Platform` sunt repository-uri distincte;
- Onyx-PMORG este workspace-ul principal, Odoo rămâne formal/fallback;
- CE-only se aplică MVP-ului și datelor sintetice; strategia pentru date reale
  necesită decizie separată de permission-aware retrieval/licențiere;
- longitudinalitatea deterministă este parte din MVP, nu etapă opțională.

## 12. Variabile rămase, fără ambiguitate de cerință

Următoarele se decid în bootstrap și se fixează în manifest:

- tagul/SHA Onyx calificat;
- commitul și digestul Odoo;
- versiunea PostgreSQL/search/object store;
- numele finale ale pachetelor și tabelelor;
- modelul/providerul pentru Gate G;
- forma exactă a adaptorului Hermes pentru Gate H;
- primul canal real pentru Gate I.

Niciuna nu poate modifica ownership-ul, closed world-ul, contractele de
business sau gate-urile fără ADR și baseline nou.

## 13. Readiness pentru implementare

`RB-1` este requirements-ready: cerințele, semantica schemelor, scenariile,
tranzițiile și pragurile sunt definite în această suită. Nu mai există o
decizie de produs deschisă care să blocheze Gates A–F.

Prima etapă de implementare materializează, fără reinterpretare:

1. contractele din `09-CONTRACTS.md` ca JSON Schema și contract tests;
2. XNX și celelalte profiluri ca YAML public, oracle privat și `world.lock`;
3. state machines/politicile ca tabele executabile și teste de tranziție;
4. criteriile A–F ca probe automate și artefacte de verdict;
5. repository-ul `PMORG-Platform` dintr-un Onyx upstream curat și fixat.

Acestea sunt livrabile de implementare, nu clarificări suplimentare ale
cerinței.
