# PMORG v3 — politica fork-ului Onyx

| Câmp | Valoare |
|---|---|
| Status | Accepted — requirements baseline `RB-1/C2` |
| Versiune | `3.0-baseline.3` |
| Data | 2026-07-19 |

## 1. Obiectiv

PMORG trebuie să poată modifica profund experiența și pipeline-ul Onyx fără
să transforme fiecare upgrade într-o rescriere. Soluția este un **thin,
governed fork**: PMORG este first-class, dar modificările upstream sunt
delimitate, inventariate și protejate prin teste.

„Thin” nu înseamnă că PMORG este superficial. Înseamnă că semantica proprie
stă în module PMORG, iar fișierele upstream sunt atinse numai în seams
explicite.

## 2. Repository-uri

Modelul acceptat în `RB-1/C2` este:

| Repo | Responsabilitate |
|---|---|
| `PMORG` | specificații, contracte, evaluation assets și referințe v1/v2 |
| `PMORG-Platform` | fork-ul Onyx și implementarea v3 |

`PMORG-Platform` păstrează istoria Git Onyx. Fiecare build fixează
`pmorg_spec_commit`; fiecare run bundle fixează ambele repository-uri.

Structura recomandată pentru implementation repo:

```text
PMORG-Platform/
├── backend/
│   ├── onyx/                       # upstream-owned; patch minim
│   └── pmorg/
│       ├── domain/                 # fără importuri Onyx/Odoo/orchestrator concret
│       ├── application/
│       ├── semantic_core/
│       ├── interaction/            # Turn Coordinator
│       ├── policy/
│       ├── integrations/
│       │   ├── onyx/
│       │   ├── odoo/
│       │   ├── orchestrator/
│       │   └── gateway/
│       ├── server/
│       └── mcp/
├── web/                            # upstream + suprafețe PMORG delimitate
├── odoo/addons/
│   ├── pmorg_core/
│   ├── pmorg_orchestrator_api/
│   ├── pmorg_memory_bridge/
│   └── pmorg_anchor_*/
├── services/
│   ├── semantic-core/
│   ├── orchestrator-adapters/      # Hermes poate fi un adaptor
│   └── communication-gateway/
├── contracts/
│   ├── context/
│   ├── events/
│   ├── memory-mcp/
│   ├── odoo/
│   ├── orchestrator/
│   └── channel/
├── evaluation/
├── deployment/
└── upstream/
    ├── BASELINE.yaml
    └── PATCH-LEDGER.md
```

Structura exactă se adaptează layoutului tagului Onyx calificat. Granițele de
ownership nu se schimbă.

## 3. Reguli de dependență

- `pmorg.domain` nu importă Onyx, Odoo ori Hermes.
- Semantic Core nu importă modelele de persistență Onyx.
- adaptoarele pot implementa porturile PMORG folosind API-urile sistemelor;
- codul Onyx apelează PMORG prin seams inventariate;
- modulele, regulile și tipurile de domeniu PMORG există exclusiv în
  rădăcinile PMORG-owned; fișierele upstream pot conține numai wiring-ul minim
  al seam-urilor allowlisted, verificat prin boundary scan și patch ledger;
- Odoo este accesat numai prin API, niciodată prin conexiune directă la DB;
- nu există foreign keys între bazele Odoo, Onyx și Semantic Core;
- modificarea unui fișier upstream în afara seam allowlist-ului este refuzată;
  extinderea allowlist-ului cere ADR, boundary-policy update, patch ledger și
  teste protectoare înainte de build, nu o excepție declarată ulterior.

## 4. Remote-uri și baseline

```text
origin   = repository-ul PMORG-Platform
upstream = https://github.com/onyx-dot-app/onyx
```

Bootstrap-ul pornește dintr-un release tag și SHA exact, calificate. Nu se
urmărește `main` și nu se folosește `latest` în imagini.

`upstream/BASELINE.yaml` conține cel puțin:

```yaml
onyx_tag: vX.Y.Z
onyx_commit: <full-sha>
pmorg_base_commit: <full-sha>
qualified_at: <date>
image_digests: {}
license_inventory_hash: sha256:...
```

Versiunea PMORG și versiunea upstream sunt independente și apar ambele în UI,
logs, artefacte și run bundle.

## 5. Politica de sincronizare

1. se creează `upstream-sync/onyx-X.Y.Z` din `main`;
2. se importă upstream prin merge auditat, nu prin rebase care ascunde
   proveniența;
3. se actualizează `BASELINE.yaml` și `PATCH-LEDGER.md`;
4. rulează suita upstream nealterată;
5. rulează contractele și gate-urile PMORG pe cele trei profiluri;
6. se verifică schema/migrările, licențele, SBOM și imaginile;
7. se face review explicit al diff-urilor în seams;
8. numai apoi branch-ul intră în `main`.

Cadenta recomandată este lunară. Patchurile de securitate sunt evaluate
imediat. Nicio sincronizare nu ajunge automat în `main` sau producție.

## 6. Patch ledger

Pentru fiecare fișier upstream modificat se consemnează:

```text
path · motiv · owner · upstream issue/PR, dacă există
license_class · ownership terms pentru patch · suprafață Onyx
seam folosit · test protector · data ultimei revalidări
conflict/rebase notes · plan de eliminare, dacă este temporar
```

Se contribuie upstream schimbările generice utile — hooks, extension seams,
bugfixuri — fără a muta semantica PMORG în upstream. Patchurile directe asupra
codului Onyx EE sunt marcate `license_class=onyx-enterprise` și nu sunt
revendicate drept cod PMORG independent; modificările și patchurile rămân sub
termenii Onyx Enterprise. Patch budget-ul se raportează la fiecare release:
număr de fișiere și linii upstream atinse, conflicte și timp de integrare.

### Capability disposition

Un catalog versionat enumeră fiecare capabilitate necesară produsului și
cerințele PMORG pe care le deservește. Setul cerințelor aplicabile este derivat
din baseline printr-o regulă fixată; nu poate fi micșorat de generatorul
catalogului. Pentru fiecare element, release-ul emite exact un record cu:
candidate search peste corpus/commit/suprafețe fixate, rezultatele brute și
clasificarea hiturilor, candidații Onyx și referințele lor de cod, verdictul de
calificare, decizia `reuse|patch|pmorg_independent`, clasa de licență și
testele/evidence. Zero candidați este un rezultat valid numai cu search evidence
complet și `pmorg_independent`. Orice `patch` ori `pmorg_independent` în
prezența unui candidat `pass` cere ADR/waiver. Lipsa unui element, o cerință
nemapată, evidence dangling ori o decizie nedeclarată invalidează `G3-A`.

Raportul include și proveniența tuturor căilor PMORG-owned. Scanul compară
hash-uri și fingerprints normalizate cu arborii EE fixați; o potrivire exactă
sau similaritate peste prag intră în review de proveniență și blochează
calificarea până la rezolvare. `licensed_patch` este permis numai pentru o
modificare directă într-o cale upstream EE, cu unicul owner din patch ledger,
bloburile fixate și `license_class=onyx-enterprise`; nu poate reclasifica o
copie EE aflată într-o cale PMORG-owned. Path inventory, match records și
evidence bytes sunt content-addressed și au coverage exact. Acest control nu
revendică ownership asupra patchurilor EE.

## 7. Licențiere

Repository-ul Onyx declară:

- conținutul din directoarele `ee` este sub Onyx Enterprise License;
- `backend/ee`, `web/src/app/ee` și `web/src/ee` conțin copii ale acelei
  licențe;
- conținutul din afara acelor restricții este disponibil sub MIT Expat, cu
  păstrarea notice-ului și a licenței;
- componentele third-party își păstrează propriile licențe.

Surse oficiale: [licența repository-ului Onyx](https://github.com/onyx-dot-app/onyx/blob/main/LICENSE)
și [Onyx Enterprise License](https://github.com/onyx-dot-app/onyx/blob/main/backend/ee/LICENSE).

Politica de build declară două axe independente:

1. `onyx_surface: ce|ee`;
2. `usage_mode: development_test|production`;
3. `ce` exclude directoarele/importurile EE și este scanat în source tree,
   dependency graph și fiecare layer salvat;
4. orice build cu `onyx_surface: ee` inventariază complet capabilitățile,
   fișierele, dependențele, patchurile și layers EE;
5. orice `usage_mode=development_test`, CE sau EE, admite numai sandbox și
   registry/destinație sintetice și refuză client deployment/distribution;
6. `ce + production` cere release/deployment admission legat de setul de
   artefacte și ținta client;
7. `ee + production` cere suplimentar autorizare verificabilă pentru entitate,
   seats/scope și acord;
8. o capabilitate Onyx se reutilizează implicit numai dacă trece contractele
   PMORG, izolarea, securitatea și constrângerile comerciale; abaterea cere ADR
   sau waiver versionat;
9. codul EE nu se copiază în module PMORG, iar patchurile directe EE rămân sub
   termenii Onyx Enterprise;
10. axele și dovezile care decid PASS sunt legate de setul exact de artefacte
    prin manifest și envelope semnat, detașate de imaginile calificate;
11. deploy/startup/watchdog reconstruiesc payloadul runtime și
    descriptor/fingerprint-ul țintei, apoi validează measurement și
    `DeploymentAdmissionRecord` prin payload + DSSE;
    publicarea/exportul reconstruiește bytes/subsetul distribuit și
    descriptorul/fingerprint-ul destinației din APIs trusted, apoi validează
    separat measurement + `DistributionAdmissionRecord` înaintea primului byte
    și revalidează până la commit, cu quiesce/abort înainte de deadline;
12. notice-ul Onyx și licențele third-party sunt păstrate; înaintea primei
    producții sau distribuții comerciale se face review juridic al buildului
    concret.

Un risc important: documentația Onyx indică faptul că RBAC-ul pentru agenți,
actions și documente și accesul diferențiat la documente sunt funcții
Enterprise. Vezi [Onyx Access Controls](https://docs.onyx.app/security/architecture/access_controls).
Prin urmare, `ce` folosește corpus sintetic cu acces uniform până când
permission-aware retrieval este calificat. Suprafața `ee` poate folosi
controlul de acces Onyx existent, dar îl califică independent.

Un „client deployment” este orice țintă care conține ori poate accesa date,
identități, canale, credențiale sau endpointuri organizaționale nesintetice.
Orice resursă necunoscută ori imposibil de măsurat clasifică ținta fail-closed
drept client. Descriptorul canonic acoperă workload identity, bindingurile de
date/identitate/canal/secrets, resource-classification report și network policy;
fingerprint-ul său se recompută independent la deploy și la fiecare startup.

Ambele suprafețe în `development_test` cer measurement attestation semnată
pentru sandbox și refuză targetul client. Publicarea/exportul cere admission
separat și permite numai registry/destinație sintetică controlată.
`ce + production` cere admission de release; `ee + production` cere
suplimentar autorizare Onyx Enterprise. Dovezile sunt content-addressed, au
trust root, timp trusted, valabilitate și revocation status; URI-urile singure
nu sunt evidence. Câmpurile comerciale sunt opace/HMAC și rămân sealed.
Verificarea pozitivă și refuzurile folosesc numai fixtures, ținte și
credențiale sintetice. ACL-ul Odoo și izolarea PMORG rămân obligatorii.

## 8. Gate-uri pentru fiecare upgrade

### Fork și build

- build upstream curat înainte de aplicarea modificărilor PMORG;
- conformitate exhaustivă cu cele patru celule: zero EE pentru `ce`; inventar
  complet pentru orice `ee`; target/distribution sintetic pentru ambele
  `development_test`; release admission pentru `ce + production`;
  autorizare Enterprise suplimentară pentru `ee + production`;
- două builduri curate reproduc descriptorii, artifact-set/image-lock,
  qualification bundle index și toate report payload hashes;
- build attestation, runtime/distribution payload measurement, target/destination
  measurement și admissions DSSE validează
  missing/not-yet-valid/expired/revoked/mismatch/untrusted, cu trusted-time
  receipts și watchdog/abort la revalidation deadline;
- capability search/disposition și provenance reports au denominatori externi,
  coverage bilateral, nested evidence byte-closed și zero cod EE copiat;
- boundary scan-ul are zero semantică PMORG sub rădăcini upstream și fiecare
  schimbare upstream aparține seam allowlist-ului și patch ledger-ului;
- toate imaginile și dependențele fixate;
- nicio modificare upstream neinventariată;
- testele upstream și PMORG verzi.

### Date

- ownership-ul Odoo/Semantic Core/Onyx nu se schimbă implicit;
- Semantic Ledger se restaurează independent;
- indexul se reconstruiește complet;
- migrările sunt forward-tested și restore-tested;
- nicio migrare upstream nu citește ori mută ledgerul PMORG fără ADR.

### Produs

- Turn Coordinator nu poate fi ocolit;
- OrganizationContext rămâne obligatoriu;
- tool preflight și comanda Odoo controlată rămân active;
- memoria personală Onyx nu intră în scope-ul organizațional;
- profilurile minimal, servicii și distribuție trec același run bundle
  structural înainte și după upgrade.

### Securitate

- cross-tenant, cross-company și unauthorized retrieval sunt refuzate;
- prompt injection nu activează un action nepermis;
- secretele și tokens nu apar în traces ori evidence;
- advisories upstream pentru baseline și dependențe sunt triaged.

### Telemetrie și egress runtime

- distribuția PMORG pornește cu telemetria/analytics upstream și update checks
  dezactivate prin configurație versionată și testată;
- la `G3-A`–`G3-F`, rețeaua SUT este deny-by-default și nu are egress; probele
  negative verifică DNS, HTTP(S) și încercările proceselor de a suna acasă;
- la `G3-G`, singurul egress permis este proxy-ul LLM declarat în manifest,
  cu allow-list, buget, redacție și jurnal local; providerul nu este accesat
  direct de servicii;
- observabilitatea rămâne locală în sandbox. Activarea unei destinații externe
  cere decizie explicită, endpoint, schema datelor, retenție și test de opt-out;
- un upgrade care adaugă endpoint, SDK sau job de telemetrie nou este schimbare
  de seam/egress și blochează calificarea până la inventariere și test.

Raportul de upgrade include configurația efectivă, conexiunile observate și
rezultatul probei de reachability. Absența unui eveniment în logul aplicației
nu este dovadă suficientă; controlul se verifică și la nivel de rețea.

## 9. Criteriul de abandon al fork-ului

Fork-ul este reevaluat dacă, pe două upgrade-uri consecutive:

- patch budget-ul ori conflictele depășesc pragul stabilit;
- seams necesare nu mai pot fi izolate;
- testele upstream nu mai pot rula fără modificări masive;
- costul de sincronizare depășește costul unei platforme proprii comparabile;
- licențierea blochează controale obligatorii fără alternativă sustenabilă.

Pragurile numerice se stabilesc după primele două sincronizări măsurate, nu
se inventează înaintea bootstrap-ului.
