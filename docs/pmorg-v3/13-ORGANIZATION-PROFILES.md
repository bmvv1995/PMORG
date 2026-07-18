# PMORG v3 — profilurile organizaționale de conformitate

| Câmp | Valoare |
|---|---|
| Status | Accepted |
| Baseline | `RB-1` |
| Suite | `ORG-CONFORMANCE-v1` |
| Data | 2026-07-18 |

## 1. Scop

Gate E demonstrează că PMORG este agnostic față de organizația concretă,
fără să fie ERP-agnostic. Același build rulează în baze curate și separate:

| Profil | Module | Scenariu |
|---|---|---|
| `ORG-MIN` | Base + Project | `MIN-ACCEPTANCE-001` |
| `ORG-SERV` | Base + Project + Employees | `SERV-DELIVERY-001` |
| `ORG-DIST` | Base + Project + Employees + Inventory | [`ORG-DIST-XNX-v1`](10-XNX-REFERENCE-SCENARIO.md) |

Profilurile diferă numai prin manifest, module, anchor packs, politici și
date. Commiturile, imaginile și pachetul de contracte sunt identice.

## 2. Traseul comun obligatoriu

Fiecare scenariu execută același traseu abstract:

```text
inițiativă
→ task de clarificare
→ mesaj și răspuns ambiguu
→ întrebare de clarificare
→ evidence
→ claim candidat
→ validare independentă
→ task/acțiune formală controlată
→ dovadă de rezultat
→ outcome verification
→ închidere
```

În fiecare profil se testează și:

- identity binding structural;
- registry negotiation și tip absent;
- claim fără auto-validare;
- command retry idempotent;
- închidere refuzată fără criteriu/dovadă;
- restart înaintea outcome verification;
- timeline complet.

## 3. `ORG-MIN / MIN-ACCEPTANCE-001`

### 3.1 Manifest și identități

```yaml
profile_id: ORG-MIN
organization: Atelier Minimal Test SRL
modules: [base, project]
anchor_packs: [pmorg_core]
policy: ORG-MIN-v1
```

| ID | Rol |
|---|---|
| `id.ana_dobre` | owner și project manager |
| `id.victor_neagu` | participant/responsabil task |
| `id.paul_rusu` | validator criteriu și outcome |
| `id.pmorg_agent` | agent de clarificare |

Identitățile folosesc `res.partner`/`pmorg.identity`; nu există
`hr.employee`.

### 3.2 Fixture public

| External ID | Model | Date |
|---|---|---|
| `project.min_site` | `project.project` | „Microsite prezentare” |
| `task.min_draft` | `project.task` | „Livrează schița paginii”; responsabil Victor; fără criteriu măsurabil |
| `initiative.min_001` | `pmorg.initiative` | „Clarifică acceptarea schiței” |

Obiectivul este să transforme „să arate bine și să fie completă” într-un
criteriu verificabil, fără HR, Inventory ori alt vocabular de domeniu.

### 3.3 Adevăr privat și dialog

Victor știe că schița acceptabilă trebuie să conțină trei secțiuni și să fie
utilizabilă la viewport de 390 px, dar nu oferă spontan detaliul.

```text
MIN-M1 PMORG → Victor:
„Ce trebuie să conțină exact schița pentru a putea fi acceptată?”

MIN-M2 Victor → PMORG:
„Să arate bine și să fie completă.”

MIN-M3 PMORG → Victor:
„Ce elemente putem verifica obiectiv și pe ce dimensiune de ecran?”

MIN-M4 Victor → PMORG:
„Header, prezentarea serviciului și contact; la 390 px fără scroll orizontal.”
```

### 3.4 Expected state

- `C-MIN-01`, kind `decision`, conține criteriul normalizat și trece
  `proposed → under_review → validated` prin Paul;
- PMORG creează o versiune nouă a criteriului/taskului numai după approval;
- Victor confirmă criteriul;
- evidence sintetică de rezultat conține structura celor trei secțiuni și
  testul viewport;
- Paul verifică outcome-ul și inițiativa se închide;
- registry-ul conține numai `IDENTITY`, `INITIATIVE`, `PROJECT`, `TASK`;
- încercările `EMPLOYEE`, `INVENTORY_TRANSFER` și `LEAVE_REQUEST` sunt refuzate
  ca ancore/actions, dar pot rămâne text brut etichetat necanonic.

## 4. `ORG-SERV / SERV-DELIVERY-001`

### 4.1 Manifest și identități

```yaml
profile_id: ORG-SERV
organization: Lumina Advisory Test SRL
modules: [base, project, hr]
anchor_packs: [pmorg_core, pmorg_anchor_hr]
policy: ORG-SERV-v1
```

| ID | Rol |
|---|---|
| `id.ioana_pavel` | owner proiect/inițiativă |
| `id.teodora_marin` | consultant și responsabil livrabil |
| `id.radu_ene` | validator și project director |
| `id.pmorg_agent` | agent de clarificare/urmărire |

Primele trei identități sunt legate neambiguu de `hr.employee` prin HR pack.

### 4.2 Fixture public

| External ID | Model | Date |
|---|---|---|
| `project.serv_audit` | `project.project` | „Analiză operațională client A” |
| `task.serv_report` | `project.task` | raport intermediar; termen 2026-03-10; incomplet |
| `initiative.serv_001` | `pmorg.initiative` | „Clarifică întârzierea raportului” |
| `document.serv_inputs` | evidence reference | inputurile clientului au fost înregistrate la 2026-03-09 |

### 4.3 Adevăr privat și dialog

Teodora știe că inputurile târzii fac termenul imposibil și poate livra pe 13
martie, dar răspunde inițial vag.

```text
SERV-M1 PMORG → Teodora:
„Raportul nu este finalizat. Ce blochează livrarea și ce termen poți confirma?”

SERV-M2 Teodora → PMORG:
„Mai am nevoie de puțin timp; au venit datele târziu.”

SERV-M3 PMORG → Teodora:
„Ce date au sosit, când, și ce dată exactă poți confirma pentru raport?”

SERV-M4 Teodora → PMORG:
„Fișierul de costuri a sosit pe 9 martie. Confirm livrarea raportului pe 13 martie, ora 16:00.”
```

### 4.4 Expected state

- `C-SERV-01`, kind `fact`: inputul critic a sosit pe 9 martie; este susținut
  de mesaj și evidence reference și validat de Radu;
- `C-SERV-02`, kind `commitment`, creează `K-SERV-01` confirmat, cu termen
  13 martie 16:00;
- schimbarea termenului taskului cere approval Ioana și plan version nou;
- o comandă duplicată modifică termenul o singură dată;
- deliverable-ul final are content hash și receipt;
- Radu verifică outcome-ul, iar inițiativa se închide;
- registry-ul adaugă `EMPLOYEE` și `DEPARTMENT`, dar nu Inventory/Time Off;
- `INVENTORY_TRANSFER` și `LEAVE_REQUEST` sunt refuzate canonic.

## 5. `ORG-DIST / ORG-DIST-XNX-v1`

Profilul distribuție folosește integral
[scenariul XNX](10-XNX-REFERENCE-SCENARIO.md). El adaugă HR și Inventory,
contradicție, supersession, conflict de versiune, follow-up/escaladare și
recovery pe 30 de zile virtuale.

## 6. Matricea registry așteptată

| Tip | MIN | SERV | DIST |
|---|---:|---:|---:|
| `IDENTITY` | yes | yes | yes |
| `INITIATIVE` | yes | yes | yes |
| `PROJECT` | yes | yes | yes |
| `TASK` | yes | yes | yes |
| `EMPLOYEE` | no | yes | yes |
| `DEPARTMENT` | no | yes | yes |
| `INVENTORY_PRODUCT` | no | no | yes |
| `INVENTORY_LOCATION` | no | no | yes |
| `INVENTORY_TRANSFER` | no | no | yes |
| `INVENTORY_MOVE` | no | no | yes |
| `LEAVE_REQUEST` | no | no | no |

Fiecare `no` înseamnă zero ancore/actions/formalizări și zero control UI
tipizat. Nu interzice apariția termenului în evidence brută sau ca
`external_mention`.

## 7. Regula aceluiași build

Pentru Gate E, reportul dovedește:

```text
pmorg_platform_commit: identic
onyx_tag_and_sha: identic
odoo_revision_and_image_digest: identic
pmorg_contract_digest: identic
semantic_schema_version: identic
image_digests: identice
```

Pot diferi numai:

```text
profile manifest · module instalate · anchor packs activate
policy values · fixture/world.lock · organization/instance IDs
```

Sunt interzise rebuildul per profil, branch-uri per client, condiții cu numele
organizației și date cross-profile.

## 8. Expected verdict

Fiecare profil rulează de 3 ori din volume curate. Gate E este PASS numai
dacă:

- toate cele 9 runuri trec traseul comun;
- registry-ul corespunde exact matricei;
- nu există concepte fantomă;
- proiecțiile și timeline-urile sunt izolate;
- redenumirea organizației nu schimbă verdictul;
- diferențele de rezultat sunt exclusiv cele declarate de profil și fixture.
