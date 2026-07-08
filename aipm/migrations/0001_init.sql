-- AI-PM v1 — schema inițială. DDL per plan A.§3 + SPEC §1.2.
-- Forward-only. Inventarul de ancore și pragurile se schimbă DOAR prin migrare (SPEC §1.1).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid pe PG < 13 compat; inofensiv altfel

-- SPEC §1.2 — inventarul de tipuri de ancoră (închis și guvernat)
CREATE TABLE anchor_type (
  code                  text PRIMARY KEY,
  odoo_model            text NOT NULL UNIQUE,
  label_ro              text NOT NULL,
  resolution_fields     text[] NOT NULL,
  disambiguation_fields text[] NOT NULL,
  has_chatter           boolean NOT NULL,
  url_template          text NOT NULL,
  accept_threshold      numeric(3,2) NOT NULL,
  review_threshold      numeric(3,2) NOT NULL,
  active                boolean NOT NULL DEFAULT true
);

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
  embedding          vector(1024),
  receipt_attempts   smallint NOT NULL DEFAULT 0,
  created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX memory_item_hash_active_uq ON memory_item(content_hash) WHERE status='active';
CREATE INDEX memory_item_embedding_idx ON memory_item USING hnsw (embedding vector_cosine_ops);
CREATE INDEX memory_item_source_ref_idx ON memory_item(source_ref);

CREATE TABLE kind_subject_allowed (
  kind        text NOT NULL,
  anchor_code text NOT NULL REFERENCES anchor_type(code),
  PRIMARY KEY (kind, anchor_code)
);

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
CREATE INDEX memory_anchor_lookup_idx ON memory_anchor(anchor_code, odoo_res_id);

-- Constrângerile de rol (SPEC §1.4 + §1.5) — seedate, nu convenție
CREATE FUNCTION memory_anchor_role_check() RETURNS trigger AS $$
DECLARE item_kind text;
BEGIN
  SELECT kind INTO item_kind FROM memory_item WHERE id = NEW.memory_id;
  IF NEW.role = 'subject' THEN
    IF NOT EXISTS (SELECT 1 FROM kind_subject_allowed
                   WHERE kind = item_kind AND anchor_code = NEW.anchor_code) THEN
      RAISE EXCEPTION 'kind_subject_not_allowed: % x %', item_kind, NEW.anchor_code;
    END IF;
  ELSIF NEW.role = 'owner' THEN
    IF item_kind <> 'commitment' THEN
      RAISE EXCEPTION 'owner_requires_commitment: kind=%', item_kind;
    END IF;
    IF NEW.anchor_code NOT IN ('PARTNER','EMPLOYEE') THEN
      RAISE EXCEPTION 'owner_type_not_allowed: %', NEW.anchor_code;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER memory_anchor_role_check_trg
  BEFORE INSERT ON memory_anchor
  FOR EACH ROW EXECUTE FUNCTION memory_anchor_role_check();

-- Chitanța: unde a fost postat FACTUAL (proveniență istorică).
-- Fără FK spre memory_anchor: reassign/remove pe ancoră nu e blocat de chitanța postată.
CREATE TABLE memory_receipt (
  memory_id       uuid PRIMARY KEY REFERENCES memory_item(id),
  anchor_code     text NOT NULL,
  odoo_res_id     integer NOT NULL,
  mail_message_id integer NOT NULL,
  posted_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ingest_log (
  id           bigserial PRIMARY KEY,
  source_type  text NOT NULL,
  source_ref   text NOT NULL,
  status       text NOT NULL CHECK (status IN ('done','extract_failed','no_items','retrying','error')),
  attempts     smallint NOT NULL DEFAULT 0,
  items_count  smallint NOT NULL DEFAULT 0,
  detail       text,
  processed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_type, source_ref)
);

CREATE TABLE ingest_cursor (
  source_type     text PRIMARY KEY,
  last_message_id integer NOT NULL DEFAULT 0,
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Entități din afara lumii Odoo (SPEC §1.7): DOAR zero-candidați (§1.6.2)
CREATE TABLE external_entity_mention (
  id              bigserial PRIMARY KEY,
  normalized_text text NOT NULL,
  memory_id       uuid NOT NULL REFERENCES memory_item(id) ON DELETE CASCADE,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX external_entity_mention_text_idx ON external_entity_mention(normalized_text);

CREATE TABLE external_entity_status (
  normalized_text text PRIMARY KEY,
  status          text NOT NULL DEFAULT 'open' CHECK (status IN ('open','dismissed','created'))
);

-- E3: overlay-ul de guvernanță — mic, explicit, uman-aprobat, versionat
CREATE TABLE rule (
  id               serial PRIMARY KEY,
  code             text UNIQUE NOT NULL,
  body_ro          text NOT NULL,
  status           text NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired')),
  version          integer NOT NULL DEFAULT 1,
  approved_by      text NOT NULL,
  approved_at      timestamptz NOT NULL DEFAULT now(),
  source_memory_id uuid REFERENCES memory_item(id)
);
