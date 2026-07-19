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
│       ├── domain/                 # fără importuri Onyx/Odoo/Hermes
│       ├── application/
│       ├── semantic_core/
│       ├── interaction/            # Turn Coordinator
│       ├── policy/
│       ├── integrations/
│       │   ├── onyx/
│       │   ├── odoo/
│       │   ├── hermes/
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
│   ├── hermes-adapter/
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
- Odoo este accesat numai prin API, niciodată prin conexiune directă la DB;
- nu există foreign keys între bazele Odoo, Onyx și Semantic Core;
- modificarea unui fișier upstream în afara allowlist-ului cere ADR sau
  actualizarea explicită a patch ledger-ului.

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
seam folosit · test protector · data ultimei revalidări
conflict/rebase notes · plan de eliminare, dacă este temporar
```

Se contribuie upstream schimbările generice utile — hooks, extension seams,
bugfixuri — fără a muta semantica PMORG în upstream. Patch budget-ul se
raportează la fiecare release: număr de fișiere și linii upstream atinse,
conflicte și timp de integrare.

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

Politica profilurilor de livrare:

1. fiecare build declară exact un profil `ce` sau `licensed-ee`;
2. profilul `ce` exclude directoarele și importurile EE și este scanat în
   source tree, dependency graph și imagini;
3. profilul `licensed-ee` inventariază capabilitățile și fișierele EE folosite,
   fără a le copia în module PMORG;
4. o capabilitate Onyx adecvată se reutilizează; nu se rescrie numai pentru a
   evita EE;
5. notice-ul Onyx și licențele third-party sunt păstrate, iar brandul
   produsului este PMORG cu atribuirea cerută;
6. activarea EE într-un deployment client cere licență/autorizare comercială
   înainte de livrare;
7. înaintea primei distribuții comerciale se face review juridic al buildului
   concret, nu numai al intenției arhitecturale.

Un risc important: documentația Onyx indică faptul că RBAC-ul pentru agenți,
actions și documente și accesul diferențiat la documente sunt funcții
Enterprise. Vezi [Onyx Access Controls](https://docs.onyx.app/security/architecture/access_controls).
Prin urmare, profilul `ce` folosește corpus sintetic cu acces uniform până
când permission-aware retrieval este calificat. Profilul `licensed-ee` poate
folosi controlul de acces Onyx existent, dar trebuie să-l califice independent
și să închidă poarta comercială înainte de deployment client. ACL-ul Odoo și
izolarea PMORG rămân obligatorii în ambele profiluri.

## 8. Gate-uri pentru fiecare upgrade

### Fork și build

- build upstream curat înainte de aplicarea modificărilor PMORG;
- conformitate cu profilul declarat: zero cod EE pentru `ce`; inventar complet
  și autorizare de deployment pentru `licensed-ee`;
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
