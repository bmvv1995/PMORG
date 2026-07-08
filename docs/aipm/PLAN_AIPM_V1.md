# Plan de implementare — AI-PM v1 (Odoo-anchored)

## Context

Repo-ul conține **nous** — laboratorul încheiat (chatbot ancorat ontologic pe GraphDB, Fazele 1–4 DONE). nous a validat mecanismele: LLM-ul produce doar candidați cu scoruri, pragurile declarative decid, poartă umană, provenance. nous rămâne donor de pattern-uri (`engine/llm.py`), nu bază de cod.

**AI-PM** este produsul succesor (docs/INTENT_AIPM.md + docs/SPEC_AIPM.md): un AI Project Manager ancorat în Odoo, care persistă ceea ce ERP-ul nu stochează — decizii, angajamente, context — fiecare element de memorie legat de înregistrări Odoo reale. Obiectiv: **instrument de producție rapid**. SPEC §0–§1 sunt închise (lege); §2–§8 sunt de decis — acest plan le decide.

Planul a fost **verificat adversarial** (40 de agenți: 4 lentile de review × refutare per constatare); 31 de constatări confirmate (5 critice) sunt integrate în textul de mai jos.

## Decizii închise (ale utilizatorului)

1. Codul: director nou `aipm/` în acest repo.
2. Stocare memorie: PostgreSQL + pgvector, schemă custom conform SPEC §1 (nu Cognee).
3. Anvergură: decizii §2–§8 + implementare fazată până la v1; faza 1 = „prima victorie" (citire ancorată + memorie de decizie pe un proiect real, poartă de scriere manuală).
4. Adaptorul Odoo = contract obligatoriu; `FakeOdooAdapter` cu fixtures e first-class (Odoo real inaccesibil din dev; verificarea reală pe serverul utilizatorului).
5. Utilizator unic în v1. UI minim viabil (HTML static + FastAPI, pattern nous).
6. Ingest din ambele surse: poll incremental `mail.message` (60s) + fața proprie de chat.
7. Bias producție-rapid: buclă subțire cap-coadă întâi; calibrare pe date reale devreme.
8. Rezoluția de entitate = nucleul critic: suită de teste măsurată din faza 1.
9. LLM: pattern provider-agnostic din nous. **Embeddings: Jina v3** (API, 1024 nativ), interfață provider-agnostică. **Pilot**: ales pe server la Faza 1. **LangSmith**: opțional prin env.

## Amendamente SPEC necesare (de aprobat explicit — §0–§1 sunt lege)

- **A1 (§0.2)**: utilizatorul de serviciu `aipm` primește și grupul `hr.group_hr_user` (read). Fără el, `hr.employee` e ilizibil pentru utilizatori interni obișnuiți în Odoo (doar `hr.employee.public`) → tipul de ancoră `EMPLOYEE` (§1.3) ar fi inutilizabil la rezoluție și la chitanțe.
- **A2 (derogare temporară de la §1.8)**: în Faza 1 chitanțele se postează exclusiv manual (decizia utilizatorului, 2026-07-07); postarea automată deterministă per §1.8 se activează în Faza 2. Din Faza 2, §1.8 se aplică litera legii, inclusiv pentru ancore `needs_review` (chitanță cu `trust_label='de verificat'` — eticheta există exact pentru acest caz; acțiunea „confirmă" din /review doar curăță flag-ul, fără re-postare).

## Disciplina de limbaj

Doar definiții operaționale. Traducerea vocabularului moștenit, obligatorie în cod/spec/UI:

| Termen istoric | Obiectul tehnic |
|---|---|
| E1 | Odoo, acces exclusiv prin adaptor: read-only + `message_post`; zero copii locale |
| E2 | tabelele PG `memory_item`, `memory_anchor`, `memory_receipt` + pgvector(1024) |
| E3 | tabela `rule`, seedată prin migrare, modificată doar prin decizie umană înregistrată |
| grefier | pipeline de extracție: apel LLM cu JSON Schema strict → validare → rezoluție → insert tranzacțional |
| ancoră | rând `memory_anchor(memory_id, anchor_code, odoo_res_id, role, confidence, resolved_by, needs_review)` |
| chitanță | `message_post` pe ținta din §1.8 + rând `memory_receipt`; format exact SPEC §1.8 |
| poarta de scriere | allowlist RPC = `{message_post}`, verificată în codul adaptorului |
| ipoteză | claim fără suport Odoo / `memory_item` fără subject rezolvat (`trust=0`), etichetat în UI |
| „manual viu" / „oglindă" | nu sunt obiecte; nu apar în plan |

**Invarianți (testabili):**
- I1: nicio metodă a adaptorului în afara allowlist-ului nu e apelabilă (→ `WriteGateViolation`).
- I2: orice `claim` cu suport Odoo are tuplurile `(anchor_code, res_id, field, value)` membre ale snapshot-ului live citit în același request (mulțimea S, §4); altfel suportul se șterge și claim-ul se retrogradează/elimină.
- I3 (invariant de scriere, calea auto): pipeline-ul nu inserează niciodată `memory_anchor` cu `confidence < review_threshold` curent al tipului (`resolved_by='auto'`). Rândurile istorice rămân valide după migrări de praguri; ancorele `resolved_by='human'` sunt exceptate.
- I4: ingestul aceluiași mesaj-sursă de două ori nu produce al doilea `memory_item` (chatter: `ingest_log` unic; chat: `message_uuid` generat de CLIENT, reutilizat la retry).
- I5: pollerul nu ingestează mesajele postate de utilizatorul `aipm` (anti-buclă).
- I6: cel mult o chitanță per `memory_item` (PK pe `memory_receipt` + serializare per memory_id + recuperare fetch-and-compare înainte de orice re-post).

---

## A. Deciziile pentru SPEC §2–§8

### §2 — Schema de extracție

Un apel LLM per mesaj-sursă (`llm_extract`). Intrare: text (max `MAX_SOURCE_CHARS=6000`), autor (nume + partner_id dacă e cunoscut), data, inventarul activ (`code`+`label_ro`), definițiile celor 5 `kind`. Output JSON validat cu `jsonschema` (`additionalProperties:false` peste tot):

```json
{"type":"object","required":["items"],"properties":{"items":{"type":"array","maxItems":5,"items":{
  "type":"object","required":["kind","title","body","quote","confidence","entities"],"properties":{
    "kind":{"enum":["decision","commitment","observation","open_question","rule_candidate"]},
    "title":{"type":"string","minLength":3,"maxLength":140},
    "body":{"type":"string","minLength":3,"maxLength":2000},
    "quote":{"type":"string","maxLength":500},
    "due_at":{"type":["string","null"],"format":"date"},
    "confidence":{"type":"number","minimum":0,"maximum":1},
    "entities":{"type":"array","maxItems":10,"items":{
      "type":"object","required":["role","mention_text","normalized_text","anchor_code_hint"],"properties":{
        "role":{"enum":["subject","owner","mentions"]},
        "mention_text":{"type":"string","maxLength":200},
        "normalized_text":{"type":"string","maxLength":200},
        "anchor_code_hint":{"type":["string","null"]}}}}}}}}}
```

Normalizare (în cod, după validare):
- Mesaj multi-obiect → 0..5 items; peste 5 → primele 5 după `confidence` desc.
- `body` = reformulare auto-conținută RO; `quote` = citat verbatim (proveniență).
- `due_at` doar la `commitment` și doar explicit în text; pe alt kind se ignoră.
- `anchor_code_hint` în afara inventarului → `null`.
- Exact un `subject`: 0 → item fără subject (`trust=0`, §1.6.4); >1 → primul rămâne, restul `mentions`.
- Exact 0..1 `owner`, doar la `commitment`: pe alt kind → retrogradat la `mentions`; >1 owner → primul rămâne, restul `mentions`.
- `confidence < EXTRACT_MIN_CONFIDENCE (0.50)` → item aruncat (logat).
- JSON/schema invalid → un retry de reparare (prompt + eroarea validatorului); eșec → `extract_failed` (terminal; replay posibil DOAR pentru chatter — pentru chat remediul e retrimiterea mesajului de către utilizator: uuid nou → source_ref nou).

Semnătura: `extraction.extract(source_text, author_name, author_partner_id, msg_date, anchor_inventory) -> list[ExtractedItem]`.

### §3 — Pipeline de scriere

**DDL adițional față de SPEC §1.2** (`migrations/0001_init.sql`; seed §1.3/§1.5 + `rule` R-001 în `0002_seed.sql`):

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_item (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind               text NOT NULL CHECK (kind IN ('decision','commitment','observation','open_question','rule_candidate')),
  title              text NOT NULL CHECK (char_length(title) <= 140),
  body               text NOT NULL CHECK (char_length(body) <= 2000),
  quote              text CHECK (char_length(quote) <= 500),
  due_at             date,
  status             text NOT NULL DEFAULT 'active' CHECK (status IN ('active','resolved','retracted')),
  trust              smallint NOT NULL DEFAULT 0 CHECK (trust IN (0,1)),
  source_type        text NOT NULL CHECK (source_type IN ('chatter','chat')),
  source_ref         text NOT NULL,
  author_ref         integer,
  extract_confidence numeric(3,2) NOT NULL,
  content_hash       text NOT NULL,
  embedding          vector(1024),               -- NULL = backfill pending
  receipt_attempts   smallint NOT NULL DEFAULT 0,
  created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX memory_item_hash_active_uq ON memory_item(content_hash) WHERE status='active';
CREATE INDEX memory_item_embedding_idx ON memory_item USING hnsw (embedding vector_cosine_ops);
CREATE INDEX memory_item_source_ref_idx ON memory_item(source_ref);

CREATE TABLE memory_anchor (
  id           bigserial PRIMARY KEY,
  memory_id    uuid NOT NULL REFERENCES memory_item(id) ON DELETE CASCADE,
  anchor_code  text NOT NULL REFERENCES anchor_type(code),
  odoo_res_id  integer NOT NULL,
  role         text NOT NULL CHECK (role IN ('subject','owner','mentions')),
  confidence   numeric(3,2) NOT NULL,
  resolved_by  text NOT NULL CHECK (resolved_by IN ('auto','human')),
  needs_review boolean NOT NULL DEFAULT false,
  mention_text text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX memory_anchor_one_subject ON memory_anchor(memory_id) WHERE role='subject';
CREATE UNIQUE INDEX memory_anchor_one_owner   ON memory_anchor(memory_id) WHERE role='owner';
-- trigger BEFORE INSERT pe memory_anchor:
--   role='subject' → (memory_item.kind, NEW.anchor_code) ∈ kind_subject_allowed, altfel RAISE
--   role='owner'   → memory_item.kind='commitment' AND NEW.anchor_code IN ('PARTNER','EMPLOYEE'), altfel RAISE (§1.4)

CREATE TABLE kind_subject_allowed (kind text NOT NULL, anchor_code text NOT NULL REFERENCES anchor_type(code), PRIMARY KEY (kind, anchor_code));

CREATE TABLE memory_receipt (            -- înregistrează unde a fost postat FACTUAL (proveniență istorică);
  memory_id       uuid PRIMARY KEY REFERENCES memory_item(id),
  anchor_code     text NOT NULL,         -- denormalizat: fără FK spre memory_anchor, ca reassign/remove
  odoo_res_id     integer NOT NULL,      -- pe ancoră să nu fie blocate de chitanța deja postată
  mail_message_id integer NOT NULL,
  posted_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ingest_log (
  id bigserial PRIMARY KEY, source_type text NOT NULL, source_ref text NOT NULL,
  status text NOT NULL CHECK (status IN ('done','extract_failed','no_items','retrying','error')),
  attempts smallint NOT NULL DEFAULT 0,
  items_count smallint NOT NULL DEFAULT 0, detail text, processed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_type, source_ref)
);
CREATE TABLE ingest_cursor (source_type text PRIMARY KEY, last_message_id integer NOT NULL DEFAULT 0, updated_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE external_entity_mention (id bigserial PRIMARY KEY, normalized_text text NOT NULL, memory_id uuid NOT NULL REFERENCES memory_item(id) ON DELETE CASCADE, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE external_entity_status (normalized_text text PRIMARY KEY, status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','dismissed','created')));

CREATE TABLE rule (
  id serial PRIMARY KEY, code text UNIQUE NOT NULL, body_ro text NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired')),
  version integer NOT NULL DEFAULT 1, approved_by text NOT NULL,
  approved_at timestamptz NOT NULL DEFAULT now(), source_memory_id uuid REFERENCES memory_item(id)
);
-- seed R-001: „Singura scriere Odoo permisă în v1: message_post (chitanța)."
```

**Chei de idempotență** (`source_ref`, unic per `source_type` în `ingest_log`): chatter → `mail.message:{id}`; chat → `chat:{session_id}:{message_uuid}`, unde `message_uuid` e generat de **client** (`crypto.randomUUID()` la Send, reutilizat la orice retry al aceluiași mesaj); serverul îl validează ca UUID; dacă lipsește (client non-UI), serverul generează unul — caz documentat fără garanție de idempotență.

**Dedup, două niveluri, înainte de insert per item:**
1. Exact: `content_hash = sha256(kind | subject_anchor_code:subject_res_id | lower(unaccent(title)) | lower(unaccent(body)))` (fără subject → `nosubject`). Coliziune pe indexul unic parțial (`status='active'`) → item sărit; id-ul itemului existent se scrie în `ingest_log.detail`.
2. Semantic: cosinus pgvector ≥ `DEDUP_SIM_THRESHOLD (0.90)`, restrâns la același kind + același subject + 30 zile + `status='active'` + `embedding IS NOT NULL`. Embedding indisponibil → nivelul 2 se omite la insert, dar **se aplică la backfill**: după calcularea embedding-ului unui rând, aceeași interogare; la match se păstrează rândul mai vechi, cel nou → `status='retracted'`, perechea logată.

**Pașii per mesaj-sursă** — `pipeline.ingest_message(source_type, source_ref, text, author, msg_date) -> IngestResult`:
1. Idempotență: rând `ingest_log` cu status ≠ `retrying` → return, zero efecte (`retrying` NU contează ca procesat).
2. Extracție (§2). Eroare transientă LLM → upsert `ingest_log(status='retrying', attempts+=1, detail=eroarea)`; cursorul NU avansează cât `attempts < INGEST_MAX_ATTEMPTS (5)`; la atingerea capului → `status='error'`, cursorul avansează (anti-poison-message). Output invalid după retry-ul de reparare → `extract_failed`, cursorul avansează.
3. Rezoluție per item (comportament §1.6). Candidați per tip = **uniunea dedup pe id a două ramuri**, ambele prin adaptor (semantică identică pe fake și real): (a) `name_search(model, normalized_text, limit=8, context={'active_test': False})`; (b) `search_read(model, OR de ('field','ilike',normalized_text) peste anchor_type.resolution_fields, fields=resolution_fields+['display_name'], limit=8, context={'active_test': False})` — `resolution_fields` sunt câmpuri de căutare (§1.2), nu doar de îmbogățire. Tipuri candidate: `anchor_code_hint` valid, altfel toate tipurile permise de matricea §1.5 (subject) / toate tipurile active (mentions); pentru **owner întotdeauna {PARTNER, EMPLOYEE}** — hint în afara setului = null (§1.4). **Un singur apel `llm_rescore` per item** pentru toate entitățile+candidații → scoruri 0..1; praguri din `anchor_type`: accept / review (`needs_review=true`) / drop. Zero candidați Odoo → scor 0 (§1.6.2).
4. Embedding `embed(title + '\n' + body)` (Jina v3, dim 1024); outage → `NULL` + backfill.
5. Dedup (mai sus).
6. **Insert — o singură tranzacție PG per mesaj-sursă**: `memory_item` + `memory_anchor` + `external_entity_mention` + `ingest_log('done')`. `external_entity_mention` primește DOAR entitățile cu **zero candidați Odoo** pe toate tipurile candidate (cazul scor-0 din §1.6.2 = „din afara lumii Odoo", §1.7). Entitățile cu candidați dar scor < review_threshold NU creează ancoră și NU sunt „externe" — se consemnează în `ingest_log.detail` ca eșec de rezoluție (semnal pentru cazuri noi în suita D). Item care pică pe constrângere → savepoint per item: doar el se aruncă.
7. **Chitanță — după commit** (§1.8), doar în `RECEIPT_MODE=auto` (Faza 2+; în Faza 1 `manual`, vezi A2). Precondiție: **există ancoră subject rezolvată** — fără subject → fără chitanță, `trust=0` (§1.6.4). Ținta: subject dacă `has_chatter=true`; subject pe tip fără chatter (doar COMPANY) → primul `mentions` cu chatter după confidence desc; fără nicio țintă cu chatter → fără chitanță. Format exact §1.8; `kind_ro` = {decision: „decizie", commitment: „angajament", observation: „observație", open_question: „întrebare deschisă", rule_candidate: „candidat de regulă"}; `trust_label` = „înaltă" (subject fără `needs_review`) / „de verificat" (subject cu `needs_review` — se postează, per §1.8). Corpul se trimite ca text simplu (Odoo escapează string-urile în `message_post` — verificat pe sursa Odoo 19).
   **Un singur punct de intrare pentru TOATE căile** (pipeline, retry, buton manual, confirm din review): `receipts.post_receipt(memory_id)`, serializat per memory_id cu `pg_advisory_xact_lock(hashtextextended(memory_id::text, 0))`; în interiorul lock-ului: re-check `memory_receipt` → recuperare → post → insert `memory_receipt(anchor_code, odoo_res_id, mail_message_id)` + `trust=1` (I6).
   **Recuperare anti-dublă-postare** (fetch-and-compare, nu ilike): `search_read('mail.message', [('model','=',m),('res_id','=',id),('author_id','=',AIPM_PARTNER_ID),('date','>=',item.created_at)], fields=['id','body'])`; în Python: strip tags + `html.unescape` + colaps spații pe fiecare body, match de **prefix exact** pe prima linie normalizată `📌 Consemnat ({kind_ro}): {title}`, excluzând `mail_message_id`-urile deja revendicate de alte chitanțe; match → se adoptă id-ul fără post nou.
   Eșec RPC → `trust=0`, `receipt_attempts+=1`, retry la ciclul următor (cap `RECEIPT_MAX_ATTEMPTS=10`, apoi vizibil în Verificare).

**Poller chatter**, la `CHATTER_POLL_SECONDS=60`:
- **Seeding la prima pornire**: dacă `ingest_cursor` nu are rând `chatter` (sau `last_message_id=0`) → se inițializează cu max `mail.message.id` curent (`search_read` limit 1, order id desc) ÎNAINTE de primul poll. Ingestul începe de la go-live; backfill istoric = acțiune manuală explicită (UPDATE cursor + `POST /api/ingest/run`), niciodată default.
- domeniu: `[('id','>',cursor),('message_type','=','comment'),('model','in',<modelele active cu has_chatter>),('author_id','!=',AIPM_PARTNER_ID)]`, `order='id asc'`, `limit=100` (I5).
- cursorul avansează după fiecare mesaj procesat (done / extract_failed / error la cap de attempts); se oprește pe mesajul curent cât e `retrying` sub cap.
- la fiecare ciclu, în `RECEIPT_MODE=auto`: retry chitanțe — `trust=0` AND subject rezolvat AND `receipt_attempts<max` AND fără `memory_receipt` AND **EXISTS ancoră (subject|mentions) cu `has_chatter=true`** (itemii fără țintă posibilă nu intră în set; dacă omul realocă ulterior o ancoră cu chatter, reintră natural). Apoi backfill embeddings (batch 20, cu dedup la backfill).
- mesaj editat/șters după procesare = limitare documentată v1 (`quote` = proveniență istorică).
- **Replay** `POST /api/ingest/replay {source_ref}` — DOAR pentru `mail.message:{id}` (chat:* → 422): re-citește mesajul prin `search_read` ÎNAINTE de a șterge rândul din log (inexistent în Odoo → refuz fără ștergere); apoi `UPDATE memory_item SET status='retracted' WHERE source_ref=$1` (determinism: itemii vechi ai sursei se retractează) și reprocesează.

**Chat propriu**: la `POST /api/chat` doar mesajul utilizatorului intră în pipeline, asincron, după trimiterea răspunsului. Capturile apar în UI prin polling: `chat.html` apelează `GET /api/memory?session_id={sid}&since={t}` ~30s după fiecare mesaj (interval 2–3s) și afișează toast per item nou. (Fără câmp `memory_captures` în răspunsul chat — ar fi self-contradictoriu cu ingestul asincron.)

### §4 — Pipeline de citire (recall)

`recall.answer(question, session) -> Answer`:
0. **Sesiune** = dict in-memory `{session_id: deque(maxlen=SESSION_MAX_TURNS=6)}` de perechi (mesaj_user, answer_ro); creată la primul mesaj fără `session_id`; pierdută la restart — limitare v1 acceptată (un singur utilizator). Ultimele tururi: (a) se antepun întrebării la rezoluție și embedding (rezolvarea pronumelor/elipselor), (b) ancorele rezolvate în tururile anterioare devin hint-uri suplimentare, (c) intră în promptul de narare ca bloc `[CONVERSAȚIE]`.
1. **Entități din întrebare**: apel dedicat `llm_query_entities(question, anchor_inventory)` cu schemă strictă `{"entities":[{mention_text, normalized_text, anchor_code_hint}], maxItems:5}` (fără kind/rol — matricea §1.5 nu se aplică întrebărilor); fiecare entitate trece prin rezolvatorul §1.6 (candidați ≥ 0.50 reținuți). JSON invalid → un retry → pasul se sare (set structural gol).
2. Recall structural: `memory_item JOIN memory_anchor` pe ancorele rezolvate (orice rol), `status='active'`, `created_at DESC`, limit 20.
3. Recall semantic: embedding întrebare (+context) → top `RECALL_TOP_K=12`, prag `RECALL_MIN_SIM=0.60`, `status='active'`. Provider căzut → doar structural + `degraded: true`.
4. **Fuziune prin cote, nu prin adunare de scoruri** (scări incomensurabile): context final = 12 items, din care până la `RECALL_STRUCT_SLOTS=6` rezervate structuralului (întâi rol `subject`, apoi `created_at DESC`), restul din semantic după similaritate; un item aflat în ambele seturi contează o dată, pe slot structural; sloturile nefolosite curg în cealaltă parte.
5. **Odoo live — precedență absolută**: helper `recall.fetch_live(anchor_code, ids)`: `search_read(model, [('id','in',ids)], fields=direct+relaționale, context={'active_test': False})`; câmpurile cu punct din `disambiguation_fields` se rezolvă în helper (many2one → `display_name` din tuplul `(id, name)`; x2many — doar `user_ids.name` la TASK în v1 → un `search_read` suplimentar batched pe comodelul din `schema()` cache-uit). Același helper servește afișarea candidaților în /review. Id absent → `deleted=true` → chip „⚠ înregistrare ștearsă din Odoo" (§1.9). Starea curentă vine EXCLUSIV de aici.
6. Narare (`llm_narrate`, JSON): context `[ODOO]` (serializat printr-o funcție canonică unică `serialize_odoo_value(field, value) -> str` — date ISO, m2o ca display_name, numere prin str; promptul cere copierea verbatim), `[MEMORIE]` (cu id-uri), `[CONVERSAȚIE]`. Output:

```json
{"answer_ro":"...","claims":[{"text":"...","status":"fact|hypothesis","support":[
  {"type":"odoo","anchor_code":"TASK","res_id":123,"field":"date_deadline","value":"2026-07-11"},
  {"type":"memory","memory_id":"<uuid>","kind":"decision"}]}]}
```

**Post-validare în cod (nu doar prompt)** — apărarea mecanică anti-halucinație (I2):
- Se păstrează mulțimea `S = {(anchor_code, res_id, field, value_str)}` construită la pasul 5. Orice suport `odoo` trebuie să fie **membru al lui S** (inclusiv valoarea, normalizată prin aceeași funcție canonică); altfel suportul se șterge.
- Claim cu ≥1 suport odoo valid → `fact`; doar `memory` (cu `memory_id` din contextul livrat) → `hypothesis`; fără suport valid → eliminat din `claims`.
- UI: `fact` → chip cu link `url_template`; `hypothesis` → badge „ipoteză".

### §5 — Contractul adaptorului Odoo

`adapter/contract.py` — exact patru metode:

```python
class OdooAdapter(Protocol):
    def schema(self, model: str) -> dict[str, dict]: ...      # fields_get; cache = viața procesului
    def search_read(self, model: str, domain: list, fields: list[str],
                    limit: int = 80, order: str | None = None,
                    context: dict | None = None) -> list[dict]: ...
    def name_search(self, model: str, name: str, limit: int = 8,
                    context: dict | None = None) -> list[tuple[int, str]]: ...
    def message_post(self, model: str, res_id: int, body: str) -> int: ...   # SINGURA scriere; body = text simplu
```

Erori tipizate: `AdapterError` ← `AdapterUnavailable`, `AdapterAccessDenied`, `WriteGateViolation`. `RPC_TIMEOUT_SECONDS=15`. Citiri: 2 retry (1s/3s) pe transiente. `message_post`: zero retry intern (retrimiterea = ciclul de ingest + recuperarea I6).

**`XmlRpcOdooAdapter`**: `xmlrpc.client` pe `/xmlrpc/2/common` + `/xmlrpc/2/object`, autentificare lazy, uid cache-uit, o re-autentificare la sesiune expirată. `AIPM_PARTNER_ID` descoperit la pornire. Cache DOAR `schema()`.

**`FakeOdooAdapter`** — first-class: fixtures JSON per model, date RO realiste acoperind suita de rezoluție (omonime, diacritice, coduri `PO00012`, arhivate); operatori `=`,`!=`,`in`,`not in`,`ilike`,`>`,`>=`,`<`; respectă `active_test`; `name_search` cu aceeași semantică declarată ca realul; `message_post` scrie într-un chatter fals in-memory interogabil prin `search_read('mail.message',...)`; injecție de defecte `fake.fail_next(method, exc, times=1)`. Selecție: `ODOO_ADAPTER=xmlrpc|fake`.

### §6 — Poarta de scriere

- În cod, pe calea unică `_execute(model, method, ...)`: `READ_METHODS={'fields_get','name_search','search_read','read','search'}`, `WRITE_ALLOWLIST={'message_post'}` (constante în `contract.py`); orice altceva → `WriteGateViolation` înainte de transport.
- Suprafața publică = cele 4 metode; fără `execute` generic.
- Apărare în adâncime: utilizatorul de serviciu §0.2 (+A1) fără drepturi de admin.
- Test pe ambele implementări: `write`/`create`/`unlink` → `WriteGateViolation`.
- Vizibilitate: `rule` R-001 expus prin `GET /api/rules`.

### §7 — Job periodic și rapoarte

**Concurență (decizie explicită)**: stack-ul pipeline rămâne **sincron** (pool psycopg3 sync `psycopg_pool.ConnectionPool`, `xmlrpc.client`, clienți LLM/embeddings sync). Bucla din lifespan nu blochează niciodată event-loop-ul: fiecare ciclu rulează prin `await asyncio.to_thread(run_ingest_cycle)`; un `threading.Lock` pe ciclu serializează și `POST /api/ingest/run` / `replay` contra pollerului. Endpoint-urile care ating DB/adaptor/LLM sunt `def` sincrone (threadpool-ul FastAPI).

**O singură buclă**: `ingest_loop` (60s: poll → pipeline → retry chitanțe → backfill embeddings). Fără snapshot zilnic în v1 (istoric/tendințe = post-v1: migrare nouă + buclă care reutilizează funcțiile pure din `reports/queries.py`).

Rapoarte = funcții pure în `reports/queries.py`, calculate la cerere, fiecare cu endpoint GET:

| cod | definiție operațională |
|---|---|
| `due_soon` | `commitment` activ cu `due_at <= current_date + DUE_SOON_DAYS(3)`, inclusiv depășite, asc |
| `commitments_missing` | `commitment` activ cu `due_at IS NULL` sau fără ancoră `owner` — două liste în payload |
| `stale_questions` | `open_question` activ mai vechi de `STALE_QUESTION_DAYS(14)` |
| `external_recurring` | `external_entity_mention GROUP BY normalized_text HAVING count(*) >= EXTERNAL_RECURRENCE_MIN(3)`, excluzând status ≠ `open`; acțiuni: dismiss / „am creat partener" (fără re-ancorare retroactivă, §1.7) |

Payload JSON = structură fixă; formularea textelor = zonă liberă.

### §8 — UI, securitate acces, endpoint-uri

**Expunere și autentificare (Faza 0, obligatoriu)**: `AIPM_BIND=127.0.0.1` (uvicorn pornit explicit pe această adresă, niciodată 0.0.0.0) + `AIPM_AUTH_TOKEN` (secret generat o dată, în `.env`); middleware FastAPI (~15 linii): orice request în afară de `GET /api/health` cere `Authorization: Bearer <token>` sau cookie `aipm_token` (setat vizitând `/?token=...` o dată). Acces remote v1 = tunel SSH `ssh -L 8090:127.0.0.1:8090 user@server` (zero infra nouă); proxy nginx pe vhost-ul existent = opțiune post-v1. Test determinist: request fără/cu token greșit → 401.

**Randare (obligatoriu, anti-XSS)**: toate șirurile dinamice (answer_ro, claims[].text, title, body, quote, display_name, mention_text, detalii review) se inserează exclusiv prin `textContent`/`createElement`; `innerHTML` cu date dinamice interzis; fără handlere inline — JS în fișiere statice separate (`web/*.js`); rutele web servite cu `Content-Security-Policy: default-src 'self'`. (Pattern-ul `esc()` ad-hoc din nous NU se portează.)

Trei pagini (stilizarea = zonă liberă; funcționalul = obligatoriu):
1. **`/` Conversație**: input + istoric; `claims[]` → chip ancoră (label_ro + display_name, link `url_template`, marcaj „⚠ ștearsă"), badge „ipoteză"; toast „📌 Consemnat: {title}" din polling-ul de capturi; clientul generează `message_uuid`.
2. **`/review` Verificare**: coada = ancore `needs_review=true` (candidați afișați prin `fetch_live`, cu `disambiguation_fields`) + items `trust=0`. Acțiuni: confirmă (`resolved_by='human'`, `confidence=1.00`, `needs_review=false`; declanșează chitanța doar dacă nu există `memory_receipt`), realocă (idem; chitanța veche, dacă există, rămâne consemnare istorică — limitare v1 documentată), șterge ancora, retractează itemul, postează chitanța (buton manual; **409 pentru itemi fără subject rezolvat**, buton dezactivat în UI).
3. **`/reports` Rapoarte**: cele 4 liste + link-uri spre Odoo și items.

```
POST /api/chat                      {message, session_id?, message_uuid?} → {session_id, answer_ro, claims[], degraded}
GET  /api/memory                    ?kind=&anchor_code=&res_id=&q=&since=&session_id=&limit=   (session_id → source_ref LIKE 'chat:{sid}:%')
GET  /api/memory/{id}
POST /api/memory/{id}/retract
POST /api/memory/{id}/post-receipt  (manual; idempotent prin I6; 409 fără subject)
GET  /api/review/queue
POST /api/review/anchor/{anchor_id} {action: confirm|reassign|remove, res_id?}
GET  /api/reports/{code}
POST /api/reports/external/{norm}/status {status: dismissed|created}
GET  /api/anchors/types
GET  /api/rules
POST /api/ingest/run                (manual; serializat cu pollerul)
POST /api/ingest/replay             {source_ref}  (doar mail.message:*; chat:* → 422)
GET  /api/health                    {pg, odoo, llm_key_set, embed_ok, cursor_lag, adapter_impl}  (fără auth)
```

Config (adăugiri peste §0): `AIPM_PORT=8090`, `AIPM_BIND=127.0.0.1`, `AIPM_AUTH_TOKEN`, `ODOO_ADAPTER`, `EMBED_API_KEY`, `EMBED_BASE_URL` (Jina v3), `EXTRACT_MIN_CONFIDENCE=0.50`, `DEDUP_SIM_THRESHOLD=0.90`, `RECALL_TOP_K=12`, `RECALL_MIN_SIM=0.60`, `RECALL_STRUCT_SLOTS=6`, `SESSION_MAX_TURNS=6`, `RPC_TIMEOUT_SECONDS=15`, `RECEIPT_MODE=manual|auto`, `RECEIPT_MAX_ATTEMPTS=10`, `INGEST_MAX_ATTEMPTS=5`, `DUE_SOON_DAYS=3`, `STALE_QUESTION_DAYS=14`, `EXTERNAL_RECURRENCE_MIN=3`.

---

## B. Structura `aipm/`

```
aipm/
├── README.md                # pornire, env, migrare, fake vs real, tunel SSH, backfill manual
├── requirements.txt         # fastapi, uvicorn, anthropic, langsmith, psycopg[binary], psycopg_pool,
│                            # pgvector, jsonschema, python-dotenv, httpx, pytest
├── .env.example
├── main.py                  # FastAPI + middleware auth + lifespan (ingest_loop via to_thread), servește web/
├── config.py                # toate variabilele, un singur loc
├── db.py                    # ConnectionPool sync, context manager tranzacție, savepoint helper, advisory lock helper
├── migrations/{migrate.py, 0001_init.sql, 0002_seed.sql}
├── adapter/{contract.py, odoo_xmlrpc.py, fake.py, fixtures/*.json}
├── engine/{llm.py, embeddings.py, extraction.py, resolution.py, pipeline.py, receipts.py, recall.py}
├── ingest/{chatter_poller.py, chat_source.py}
├── reports/queries.py
├── web/{chat.html, chat.js, review.html, review.js, reports.html, reports.js}
└── tests/{conftest.py, resolution_cases/cases.yaml, test_resolution_suite.py,
          test_extraction_schema.py, test_pipeline_idempotency.py, test_write_gate.py,
          test_receipts.py, test_recall_claims.py, test_reports.py, test_auth.py}
```

Fără LangGraph (pipeline liniar). Roluri trace LLM: `llm_extract`, `llm_query_entities`, `llm_rescore`, `llm_narrate`; LangSmith opțional prin env.

## C. Faze

Regulă transversală: CI/dev exclusiv pe `FakeOdooAdapter` + LLM real; verificarea pe instanța reală = pași manuali pe server, la finalul fiecărei faze.

**Faza 0 — Schelet.** Structura, config, db, migrații + runner, portare `llm.py`, contract + `FakeOdooAdapter` + fixtures, poarta de scriere + `XmlRpcOdooAdapter`, **middleware auth + bind 127.0.0.1**, `/api/health`, `/api/anchors/types`. Pe server: creare utilizator `aipm` per §0.2 **+ amendamentul A1 (grup HR)**.
*Verificare:* `migrate.py` pe DB goală → seed §1.3 exact; pytest verde incl. write-gate pe ambele implementări + `test_auth.py` (401).

**Faza 1 — Prima victorie (citire ancorată + memorie, `RECEIPT_MODE=manual`).** `resolution.py` + harness-ul suitei de rezoluție (din prima zi); `extraction.py`, `pipeline.py` (cu anti-poison, seeding cursor); ambele surse de ingest; `recall.py` complet (llm_query_entities, fuziune prin cote, `fetch_live`, mulțimea S, post-validare claims); UI minim (chat cu message_uuid client + review redus cu buton chitanță).
*Verificare (fake):* e2e pytest — mesaj în chatter fals → item ancorat TASK → recall cu chip + fapt live; suita de rezoluție 100% `must`, ≥85% total (min. 25 cazuri); idempotență chatter + chat (același message_uuid de 2× → un item).
*Verificare (real):* `ODOO_ADAPTER=xmlrpc`; cursor seeded la max id (istoricul NU se ingestează); alegerea proiectului-pilot; ≥10 amintiri reale ancorate corect (inspecție /review); o chitanță manuală apare în chatter cu formatul §1.8 și link funcțional; acces doar prin tunel SSH + token.

**Faza 2 — Scriere automată guvernată (`RECEIPT_MODE=auto`).** Chitanță automată la insert per §1.8 **inclusiv pentru `needs_review`** (trust_label „de verificat"; confirm din review doar curăță flag-ul); retry cu condiția EXISTS-țintă-cu-chatter; recuperare fetch-and-compare; `post_receipt` unic serializat (I6); dedup semantic + backfill cu dedup; `review.html` complet.
*Verificare (fake):* injecție de defect — post eșuat → `trust=0` → retry reușit → `trust=1` fără dublură; cursă simulată buton+retry → o singură chitanță; dedup pe reformulare; item COMPANY-fără-mentions-cu-chatter nu intră în retry.
*Verificare (real):* o zi pe pilot fără chitanțe duplicate și fără auto-ingestia chitanțelor.

**Faza 3 — Rapoarte + întărire recall.** `reports/queries.py` + endpoint-uri + `reports.html`; chip „ștearsă"; acțiuni `external_entity_status`.
*Verificare (fake):* `test_reports.py` pe date sintetice; recall pe ancoră arhivată/ștearsă randează corect.
*Verificare (real):* rapoartele pe datele pilotului au sens la inspecție.

**Faza 4 — Calibrare + guvernanță minimă.** Raport de calibrare (distribuția scorurilor vs corecțiile `resolved_by='human'`); ajustare praguri DOAR prin migrare pe `anchor_type` (§1.1) — o migrare care RIDICĂ `review_threshold` setează `needs_review=true` pe rândurile auto sub noul prag (același fișier SQL); flux minim `rule_candidate` → Verificare → aprobare = insert în `rule`.
*Verificare:* suita de rezoluție re-rulată după orice ajustare; zero regresii pe `must`.

## D. Testare (pytest)

- DB de test: PostgreSQL local cu `vector`; `conftest.py` creează schemă efemeră prin `migrate.py`.
- **Suita de rezoluție**: `cases.yaml` — `{id, severity: must|should, text, entity{mention,hint}, expect{outcome: accept|review|none, anchor, res_id}}`; pe `FakeOdooAdapter` + LLM real (`@pytest.mark.llm`). Poarta: 100% `must`, ≥85% total. Regulă permanentă: orice rezoluție greșită pe server devine caz nou.
- Deterministe (FakeLLM): praguri pe valori-limită; matricea kind×subject și regulile owner prin trigger (owner pe kind≠commitment → RAISE; owner TASK → RAISE; al doilea owner → violare index); unicitate subject; normalizare §2 (0/2 subjects, >1 owner, hint invalid, due_at pe non-commitment); formatul chitanței caracter-cu-caracter; ținta chitanței (fără subject → 409; COMPANY → mentions cu chatter → fără țintă); fuziunea prin cote (12 semantice + 3 structurale-only → toate 3 prezente); post-validarea S (suport cu valoare nefetchată → șters, claim retrogradat).
- Idempotență: același `source_ref` 2× → un item; același `message_uuid` chat 2× → un item; cursor resetat + log intact → zero reprocesări; crash între insert și chitanță → retry postează exact una; poison message → după `INGEST_MAX_ATTEMPTS` cursorul avansează.
- Poarta de scriere: ambele adaptoare, metodă ∉ allowlist → `WriteGateViolation`.
- Auth: `/api/*` fără token → 401; `/api/health` fără token → 200.
- Recall/claims: suport inexistent/valoare falsă → eliminat; contradicție memorie vs Odoo → faptul din Odoo; ancoră ștearsă → `deleted=true`.
- CI implicit = fără `@pytest.mark.llm`; suita LLM local, la orice schimbare pe `resolution.py`/`extraction.py`/prompturi.

## E. Migrații

SQL numerotat + runner propriu (~40 linii), forward-only: `schema_migration(filename, hash, applied_at)`; ordine lexicală, fiecare fișier în propria tranzacție; refuz dacă un fișier aplicat s-a modificat. Justificare: un nod/un dezvoltator/o bază; psycopg direct (fără ORM → Alembic nejustificat); §1.1 cere schimbarea inventarului/pragurilor doar prin migrare versionată — SQL-ul în git ESTE mecanismul de guvernanță. Fără down-migrations.

## F. Riscuri → mitigări

| Risc | Mitigare |
|---|---|
| Prima pornire ingestează tot istoricul horeca | seeding cursor la max id înainte de primul poll; backfill doar manual explicit |
| Serviciu expus pe serverul de producție | bind 127.0.0.1 + bearer token (exceptat doar /api/health) + tunel SSH; test 401 |
| Poison message blochează cursorul | `retrying` + `attempts` cap 5 → `error`, cursorul avansează; replay manual |
| Narator fabrică „fapte" (prompt injection din chatter) | mulțimea S: suport odoo valid doar cu tuplu (ancoră, câmp, valoare) fetchat live în același request; altfel claim retrogradat/eliminat (I2) |
| XSS din conținut LLM/Odoo în UI | textContent-only, fără innerHTML dinamic, fără inline handlers, CSP default-src 'self' |
| Rezoluție greșită (riscul #1 de credibilitate) | suită măsurată din Faza 1 (poartă 100% must); praguri în `anchor_type`; erori reale → cazuri noi; calibrare Faza 4 |
| EMPLOYEE ilizibil pentru service user | amendament A1 (§0.2): grup `hr.group_hr_user` la crearea utilizatorului |
| Chitanțe duplicate (curse: buton/retry/confirm; timeout după succes) | punct unic `post_receipt` + advisory lock per memory_id + re-check + recuperare fetch-and-compare cu prefix exact normalizat și recency bound (I6) |
| JSON invalid de la LLM | jsonschema + 1 retry de reparare + terminal `extract_failed` |
| Timeout/căderi RPC | erori tipizate; retry 2× doar citiri; poll se oprește fără avans; `cursor_lag` în health |
| Event-loop blocat de xmlrpc/LLM sync | ciclul de ingest în `asyncio.to_thread`; endpoint-uri sync în threadpool; `threading.Lock` pe ciclu |
| Cădere embeddings | `NULL` + backfill cu dedup la backfill; recall degradat structural (`degraded=true`) |
| Duplicate acumulate în outage | dedup re-rulat la backfill: rândul nou → `retracted`, pereche logată |
| Extracție mediocră la început | acceptată (buclă subțire); `EXTRACT_MIN_CONFIDENCE` + coada de Verificare țin zgomotul vizibil |
| Scriere accidentală în Odoo | allowlist pe calea unică `_execute` + user fără drepturi + test pe ambele adaptoare |

## G. Verificare end-to-end (definiția lui „done" pentru v1)

1. Pe fake: suita pytest completă verde (rezoluție ≥ poartă, idempotență, write-gate, receipts+curse, claims/S, auth, rapoarte).
2. Pe server (`horeca`): poller continuu pe pilot, cursor seeded corect; amintiri ancorate; chitanțe cu format §1.8 și link-uri funcționale; /review permite corecția; /reports reflectă datele; **nicio scriere Odoo în afara `message_post`** (verificabil în log-urile Odoo); acces doar prin tunel + token.
3. Criteriul de credibilitate: după o săptămână pe pilot, rata ancorelor corecte fără corecție umană (din /review); fiecare eroare → caz nou în suită.

## Decizii finale (clarificate cu utilizatorul, 2026-07-07)

1. **Pilot**: ales pe server la Faza 1. 2. **Embeddings**: Jina v3 (API, 1024). 3. **Poarta Fazei 1**: chitanțe doar manuale; automat din Faza 2 (amendamentul A2). 4. **LangSmith**: opțional prin env.
