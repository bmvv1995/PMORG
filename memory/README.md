# Serviciul de memorie PMORG (Gate B.1)

Memoria organizațională externă (ADR-004), contract **`pmorg-memory/1.0`**,
deterministă (fără LLM), cu persistență reală PostgreSQL.

## Garanții implementate (02-MVP §4.3)

- **Boot fail-closed**: `profile_id`, `run_id`, `instance UUID`, `namespace`,
  PG host allow-listed și politica de validatori sunt obligatorii explicit;
  lipsa oricăreia oprește serviciul înainte de rețea (exit 1). Nu există
  niciun default de producție.
- **Registry negociat per profil**: `org-min` expune doar COMPANY, PROJECT,
  TASK, INITIATIVE, IDENTITY; profil sau fingerprint diferit ⇒
  `MEM_REGISTRY_MISMATCH`; tip de ancoră din afara registry-ului ⇒
  `MEM_ANCHOR_TYPE_UNKNOWN` (fail-closed semantic, ADR-002).
- **Validare mecanică a claims**: validatorul trebuie autorizat de politică
  (`MEM_NOT_AUTHORIZED`), diferit de autor, cu dovadă de autor independent
  (`MEM_SELF_VALIDATION`) și hash verificat (`MEM_HASH_MISMATCH`).
- **Supersession fără ștergere** (ADR-005); recall etichetează mecanic
  `validated` vs `hypothesis`.
- **Idempotency** la captură: dedup pe `(namespace, external_id)`.

## Suprafața

`memory_negotiate_registry`, `memory_capture_evidence`,
`memory_propose_claim`, `memory_validate_claim`, `memory_recall`,
`memory_get_timeline`, `memory_supersede`, `memory_record_outcome`.

Transport actual: JSON-RPC 2.0 peste HTTP (`POST /`), un singur serviciu per
run/namespace. Legarea la protocolul MCP standard (stdio) este o anvelopă
subțire peste aceleași tool-uri — se adaugă la integrarea agentică (Gate E).

## Decizii asumate sub mandat (de evaluat de owner)

1. Serviciul e o implementare nouă, minimă, a contractului v2 — preia
   principiile nucleului `aipm` (evidență→claim→validare, ancore, epistemic
   labels), nu codul lui: aipm-ul actual trage după el ingest de chatter,
   LLM și configurație non-sandbox-safe (URL de producție ca default, exact
   ce interzice noul 02-MVP). Convergența cu aipm rămâne decizie separată.
2. Fără embeddings/pgvector în B.1 — recall-ul e structural (pe ancore),
   suficient pentru smoke; semantica vectorială intră când un scenariu o
   cere, cu schimbare de imagine PG (`pgvector/pgvector:pg16`).
3. Post-validarea live contra Odoo (mulțimea S din aipm) nu e încă legată —
   intră odată cu `memory_recall` folosit de un agent real (Gate E).

## Rulare (sb3)

Serviciul e în `compose.yaml` (`memory`, port `127.0.0.1:18091`), baza
`pmorg_memory`. Smoke-ul integrat: `python3 run_smoke.py --db <db>` — 25 de
verificări, inclusiv negativele de validare.
