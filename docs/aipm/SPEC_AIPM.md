# SPEC AI-PM — specificație de implementare

> Complement tehnic al `INTENT_AIPM.md`. Regula documentului: implementatorul NU ia decizii.
> Orice opțiune nespecificată aici e un defect al specificației, nu o libertate.
> Starea secțiunilor: §0–§1 = complete (v1.0, 2026-07-07). §2–§8 = planificate.

---

## §0. Mediul și variabilele de configurare

Instanța țintă (sandbox): Odoo 19 Community modules, baza `horeca`.

| Variabilă | Valoare v1 | Observații |
|---|---|---|
| `ODOO_BASE_URL` | `https://horeca.evrika.team` | folosită și la construirea URL-urilor de ancoră |
| `ODOO_RPC_URL` | `http://127.0.0.1:8069` | transportul RPC ocolește nginx/Cloudflare |
| `ODOO_DB` | `horeca` | |
| `ODOO_RPC_LOGIN` | `aipm` | utilizator de serviciu DEDICAT (nu admin) — vezi §0.2 |
| `ODOO_RPC_PASSWORD` | secret în `.env` | |
| `PG_DSN` | `postgresql://aipm:...@127.0.0.1:5432/aipm` | baza proprie a serviciului, separată de bazele Odoo |
| `EMBED_PROVIDER` / `EMBED_MODEL` | config | dimensiune vector fixată: **1024** |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | config | pattern-ul provider-agnostic din nous `engine/llm.py` |
| `CHATTER_POLL_SECONDS` | `60` | ingest incremental `mail.message` |

### §0.2 Utilizatorul de serviciu Odoo

Se creează manual, o dată: login `aipm`, tip *internal user*, grupuri: `base.group_user`,
`project.group_project_user`, `purchase.group_purchase_user`, `sales_team.group_sale_salesman`,
`crm` (user). Fără drepturi de administrare. Toate apelurile RPC (citire + `message_post`)
se fac cu acest utilizator; chitanțele apar în chatter ca „aipm". Scrierile de date (write/create
pe înregistrări de business) sunt interzise la nivel de cod în v1 (§6 — poarta), indiferent de
drepturile utilizatorului.

---

## §1. Lumea Odoo: inventarul de ancore

### §1.1 Principiu

Inventarul de tipuri de ancoră este **închis și guvernat**: o tabelă seedată la instalare,
modificabilă doar prin migrare versionată (nu la runtime, nu de LLM). Grefierul poate ancora
o amintire EXCLUSIV pe un tip din inventar. Orice model Odoo care nu e în inventar este,
pentru sistemul de memorie, invizibil ca ancoră.

### §1.2 Schema

```sql
CREATE TABLE anchor_type (
  code                  text PRIMARY KEY,      -- stabil, MAJUSCULE, nu se redenumește niciodată
  odoo_model            text NOT NULL UNIQUE,  -- ex. 'project.task'
  label_ro              text NOT NULL,         -- pentru UI
  resolution_fields     text[] NOT NULL,       -- câmpuri interogate la rezoluția de entitate
  disambiguation_fields text[] NOT NULL,       -- câmpuri afișate omului la ambiguitate
  has_chatter           boolean NOT NULL,      -- modelul moștenește mail.thread → poate primi chitanță
  url_template          text NOT NULL,         -- verificat pe Odoo 19: '{base_url}/odoo/{model}/{id}'
  accept_threshold      numeric(3,2) NOT NULL, -- ≥ → ancorare automată
  review_threshold      numeric(3,2) NOT NULL, -- ≥ → ancorare cu flag de verificare; sub → fără ancoră
  active                boolean NOT NULL DEFAULT true
);
```

`memory_anchor` primește FK: `anchor_code REFERENCES anchor_type(code)`; perechea
(`anchor_code` → `odoo_model`) face `odoo_model` din `memory_anchor` redundant — se elimină
din schema §schiței anterioare; rămâne doar `(memory_id, anchor_code, odoo_res_id, role,
confidence, resolved_by)`.

### §1.3 Inventarul v1 — valorile seed (exacte)

`url_template` este identic pentru toate: `{base_url}/odoo/{odoo_model}/{odoo_res_id}`
(verificat funcțional pe instanța horeca la 2026-07-07).

| code | odoo_model | label_ro | resolution_fields | disambiguation_fields | chatter | accept | review |
|---|---|---|---|---|---|---|---|
| `COMPANY` | res.company | Compania | name | — | nu | 0.95 | 0.70 |
| `PROJECT` | project.project | Proiect | name | user_id.name | da | 0.85 | 0.50 |
| `TASK` | project.task | Task | name | project_id.name, user_ids.name, date_deadline | da | 0.85 | 0.50 |
| `PARTNER` | res.partner | Partener | name, email, ref | city, is_company, supplier_rank, customer_rank | da | 0.85 | 0.50 |
| `EMPLOYEE` | hr.employee | Angajat | name, work_email | job_title, department_id.name | da | 0.90 | 0.60 |
| `PURCHASE_ORDER` | purchase.order | Comandă achiziție | name, partner_ref | partner_id.name, date_order, state | da | 0.90 | 0.60 |
| `SALE_ORDER` | sale.order | Comandă vânzare | name | partner_id.name, date_order, state | da | 0.90 | 0.60 |
| `LEAD` | crm.lead | Oportunitate | name | partner_name, expected_revenue | da | 0.85 | 0.50 |
| `PRODUCT` | product.template | Produs | name, default_code | categ_id.name, list_price | da | 0.85 | 0.50 |

Justificarea pragurilor (pentru posteritate, nu pentru implementator):
- 0.90+ la `EMPLOYEE`: atribuirea greșită a unei persoane e cea mai scumpă eroare socială.
- 0.90+ la ordine (`PURCHASE_ORDER`/`SALE_ORDER`): au coduri unice (`PO00012`); un match fuzzy
  sub 0.90 e aproape sigur ordinea greșită.
- 0.95 la `COMPANY`: referită rar; când e referită, trebuie certitudine.

Decizii închise:
- `PRODUCT` ancorează la **product.template**, niciodată la product.product (variante) în v1.
- `res.users` NU e tip de ancoră. Persoanele se ancorează ca `PARTNER` sau `EMPLOYEE`;
  autorul unei amintiri (`memory_item.author_ref`) e întotdeauna `res.partner.id`.
- Modele rezervate pentru extensii viitoare (NU se implementează în v1):
  `stock.picking` (LIVRARE), `account.move` (FACTURĂ), `calendar.event` (ÎNTÂLNIRE),
  `pos.session` (SESIUNE POS). Adăugarea = migrare nouă cu rând nou în seed + prag definit.

### §1.4 Rolurile ancorelor

Enum `role`: `subject` | `owner` | `mentions`.

- `subject` — despre ce e amintirea. **Exact una** per amintire ancorată (constrângere
  unică parțială: `UNIQUE (memory_id) WHERE role='subject'`). Ținta chitanței.
- `owner` — doar pentru `kind='commitment'`: cine datorează. **0..1**, obligatoriu tip
  `PARTNER` sau `EMPLOYEE`. Un commitment fără owner rezolvat se salvează, dar intră în
  raportul „angajamente fără responsabil" (§7).
- `mentions` — orice altceva atins de amintire. 0..N.

### §1.5 Matricea kind × subject (constrângere seedată, nu convenție)

Tabelă `kind_subject_allowed(kind, anchor_code)`, verificată la insert. Seed exact:

| kind | subject permis |
|---|---|
| `decision` | PROJECT, TASK, PURCHASE_ORDER, SALE_ORDER, LEAD, PRODUCT, COMPANY |
| `commitment` | TASK, PROJECT, LEAD, PURCHASE_ORDER, SALE_ORDER, PARTNER |
| `observation` | oricare din inventar |
| `open_question` | PROJECT, TASK, PURCHASE_ORDER, LEAD, PARTNER, COMPANY |
| `rule_candidate` | COMPANY, PROJECT |

`mentions` nu are restricții de tip. `due_at` este permis NULL la commitment (angajamente
fără termen există), dar acestea apar în raportul dedicat (§7) — nu se inventează termene.

### §1.6 Rezoluția de entitate — comportament definit

1. Căutarea se face prin adaptor: `name_search` + `search_read` pe `resolution_fields`,
   cu **context `active_test=False`** (înregistrările arhivate SUNT ancorabile — memoria
   se referă și la trecut).
2. Scorul final al unui candidat = scorul LLM de rescorare (0..1) pe lista candidaților
   întorși de Odoo. Fără candidați Odoo → scor 0 prin definiție (LLM-ul nu poate „ști"
   un id pe care căutarea nu l-a întors).
3. Aplicarea pragurilor (din `anchor_type`, nu din cod):
   - `score ≥ accept_threshold` → ancoră cu `resolved_by='auto'`.
   - `review_threshold ≤ score < accept_threshold` → ancoră cu `resolved_by='auto'` +
     flag `needs_review=true` (coloană pe `memory_anchor`); apare în UI la verificare.
   - `score < review_threshold` → NU se creează ancora.
4. Fără `subject` rezolvat → amintirea se salvează cu `trust=0`, fără chitanță.

### §1.7 Entități din afara lumii Odoo

Ex.: „primăria", „Narcoffee", „firma de decor". Reguli:
- NU se creează automat înregistrări Odoo (poarta de scriere, §6, e închisă pentru grefier).
- Textul rămâne în `body`; entitatea externă NU devine ancoră.
- Raportul „entități externe recurente" (§7) numără aparițiile pe text normalizat;
  la recurență, omul decide manual dacă îi creează un partener în Odoo. După creare,
  amintirile viitoare se ancorează natural; cele vechi NU se re-ancorează automat în v1.

### §1.8 Chitanța — determinism complet

- Ținta: ancora `subject`, dacă `anchor_type.has_chatter=true`.
- `subject` fără chatter (doar `COMPANY` în v1) → chitanța se postează pe prima ancoră
  `mentions` cu chatter, în ordinea confidence descrescător; dacă nu există → fără chitanță,
  `trust` rămâne 0.
- Formatul chitanței (exact):
  `📌 Consemnat ({kind_ro}): {title}` + linie nouă + `{body}` + linie nouă +
  `— aipm · încredere: {trust_label} · sursă: {source_type}`.
- `mail_message_id` întors de `message_post` se salvează în `memory_receipt`. Eșecul postării
  (excepție RPC) nu blochează insertul memoriei: `trust=0`, retry la următorul ciclu de ingest.

### §1.9 Ciclul de viață al referinței (înregistrări șterse/arhivate în Odoo)

- Ancora stochează doar `res_id`; starea E1 se citește live la recall (nu se face snapshot —
  proveniența păstrează `quote`, atât).
- La recall, `read` care nu mai găsește înregistrarea → chip-ul se randează ca
  „⚠ înregistrare ștearsă din Odoo", amintirea rămâne vizibilă și validă istoric.
  Nicio ștergere în cascadă, niciodată.
- Instanță unică în v1. La eventuală multi-instanță: coloană nouă `odoo_instance_id`
  cu default instanța curentă (migrare aditivă, documentată aici ca procedură).

---

## §2. Schema de extracție a grefierului — PLANIFICAT
JSON Schema exact al output-ului LLM, tratarea mesajelor multi-obiect, limite de lungime.

## §3. Pipeline scriere — PLANIFICAT
Pașii 1–6 (extracție → rezoluție → dedup → insert → chitanță → trust), tranzacții, idempotență.

## §4. Pipeline citire (recall) — PLANIFICAT
Fuziunea structural + semantic + E1 live; schema `claims[]` cu `support`; precedența E1.

## §5. Contractul adaptorului Odoo — PLANIFICAT
Semnăturile exacte: `schema()`, `search_read()`, `name_search()`, `message_post()`; cache; erori.

## §6. Poarta de scriere — PLANIFICAT
În v1: closed by default; enumerarea exactă a singurei scrieri permise (`message_post`).

## §7. Joburi periodice și rapoarte — PLANIFICAT
Scadențe, angajamente fără termen/responsabil, dileme stagnante, entități externe recurente.

## §8. UI — PLANIFICAT
Fața Conversație (chip-uri de ancoră, etichete ipoteză), fața Verificare (needs_review), fața Oglindă.
