# AI-PM — AI Project Manager ancorat în Odoo

Stratul de memorie guvernată peste Odoo: persistă ce ERP-ul nu stochează — decizii,
angajamente, „de ce"-uri — fiecare element ancorat la înregistrări Odoo reale, cu
chitanță în chatter și trasabilitate completă.

Documente-lege: `../docs/INTENT_AIPM.md` (arhitectura) și `../docs/SPEC_AIPM.md`
(§0–§1 închise). Deciziile §2–§8 = planul de implementare aprobat.

## Arhitectură pe scurt

- **Odoo** = sursa de adevăr, citită LIVE prin adaptor (`adapter/`); zero copii locale.
  Singura scriere permisă: `message_post` (chitanța) — impusă în cod (`WriteGateViolation`).
- **PostgreSQL `aipm`** (+pgvector 1024) = memoria: `memory_item`, `memory_anchor`,
  `memory_receipt`; inventarul de ancore (`anchor_type`) e închis și guvernat prin migrări.
- **LLM** (provider-agnostic) doar propune: extracție cu scoruri, rescorare candidați,
  narare. Pragurile din `anchor_type` decid; omul verifică în `/review`.
- Claims-urile din răspunsuri sunt post-validate mecanic contra citirii live (mulțimea S):
  fapt = doar ce există chiar acum în Odoo; restul e etichetat ipoteză.

## Pornire (dev, fără Odoo real)

```bash
pip install -r aipm/requirements.txt
# PostgreSQL 16 + extensiile vector și unaccent (creează-le un admin, o dată):
#   CREATE ROLE aipm LOGIN PASSWORD '...' ; CREATE DATABASE aipm OWNER aipm;
#   \c aipm ; CREATE EXTENSION vector; CREATE EXTENSION unaccent;
cp aipm/.env.example aipm/.env       # completează secretele
python -m aipm.migrations.migrate    # aplică 0001+0002 (seed SPEC §1.3/§1.5)
python -m aipm.main                  # http://127.0.0.1:8090/?token=<AIPM_AUTH_TOKEN>
```

Cu `ODOO_ADAPTER=fake` totul rulează pe fixtures locale (`adapter/fixtures/*.json`).

## Deploy pe server (instanța reală)

1. Utilizatorul de serviciu Odoo `aipm` per SPEC §0.2 **+ amendamentul A1**: grupurile
   `base.group_user`, `project.group_project_user`, `purchase.group_purchase_user`,
   `sales_team.group_sale_salesman`, crm user, **`hr.group_hr_user`** (fără el, tipul
   de ancoră EMPLOYEE nu poate citi `hr.employee`). Fără drepturi de administrare.
2. `.env`: `ODOO_ADAPTER=xmlrpc`, credențialele RPC, `AIPM_AUTH_TOKEN` generat.
3. Serviciul ascultă DOAR pe `127.0.0.1:8090`. Acces remote:
   `ssh -L 8090:127.0.0.1:8090 user@server` → browser `http://127.0.0.1:8090/?token=…`.
4. La prima pornire cursorul de chatter se seedează la id-ul curent maxim — istoricul
   NU se ingestează. Backfill istoric = acțiune manuală explicită:
   `UPDATE ingest_cursor SET last_message_id=<id> WHERE source_type='chatter';`
   apoi `POST /api/ingest/run`.
5. Faza 1 rulează cu `RECEIPT_MODE=manual` (chitanțe doar din butonul din /review —
   amendamentul A2); după validarea calității ancorării treci pe `auto` (§1.8 integral).

## Teste

```bash
pytest aipm/tests            # suita deterministă (FakeLLM + FakeOdooAdapter + PG efemer)
pytest aipm/tests -m llm     # suita de rezoluție (LLM real; cere LLM_API_KEY)
```

Suita de rezoluție (`tests/resolution_cases/cases.yaml`) e nucleul de credibilitate:
poarta = 100% pe cazurile `must`, ≥85% total. **Regulă permanentă: orice rezoluție
greșită pe instanța reală devine caz nou în suită.** Se rerulează la orice schimbare
pe `resolution.py`, `extraction.py` sau prompturi.

## Structură

```
main.py          bootstrap: auth (Bearer/cookie), CSP, lifespan cu bucla de ingest
api_routes.py    endpoint-urile de produs (§8)
config.py        toate variabilele (unică sursă)
db.py            pool psycopg sync, tranzacții, savepoint, advisory lock
migrations/      SQL numerotat forward-only + runner (guvernanța schemei, SPEC §1.1)
adapter/         contract (4 metode) + poarta de scriere + XmlRpc + Fake cu fixtures
engine/          llm, embeddings, extraction (§2), resolution (§1.6), pipeline (§3),
                 receipts (§1.8, idempotente I6), recall (§4, claims post-validate I2)
ingest/          poller chatter (seeding, anti-poison, anti-buclă I5) + sursa de chat
reports/         due_soon, commitments_missing, stale_questions, external_recurring (§7)
web/             UI: Conversație / Verificare / Rapoarte — textContent-only, fără inline JS
```

## Limitări v1 (documentate, asumate)

- Sesiunile de chat sunt in-memory — se pierd la restart.
- Mesaj editat/șters în Odoo după ingest nu se detectează; `quote` = proveniență istorică.
- Replay doar pentru chatter; pentru chat remediul = retrimiterea mesajului.
- Realocarea unei ancore după postarea chitanței NU repostează — chitanța veche rămâne
  consemnare istorică.
