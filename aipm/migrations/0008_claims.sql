-- Stratul de claims al contractului pmorg-memory/1.0 (convergența v2, S3).
-- ADR-005: evidență -> candidat -> validat -> superseded; nimic nu se șterge.
-- Tabele NOI lângă memory_item (memoria v1 rămâne neatinsă); namespace separă
-- run-urile/profilurile de sandbox de eventuala instanță reală.

CREATE TABLE mem_evidence (
    id             serial PRIMARY KEY,
    namespace      text NOT NULL,
    external_id    text NOT NULL,
    source         text NOT NULL,
    author_ref     text NOT NULL,
    content        text NOT NULL,
    content_hash   text NOT NULL,
    correlation_id text,
    received_at    text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (namespace, external_id)
);

CREATE TABLE mem_claim (
    id             serial PRIMARY KEY,
    namespace      text NOT NULL,
    statement      text NOT NULL,
    status         text NOT NULL DEFAULT 'candidate'
                   CHECK (status IN ('candidate','validated','refuted','superseded')),
    author_ref     text NOT NULL,
    evidence_ids   integer[] NOT NULL DEFAULT '{}',
    anchors        jsonb NOT NULL DEFAULT '[]',
    validated_by   text,
    validated_at   timestamptz,
    validation_evidence_id integer REFERENCES mem_evidence(id),
    superseded_by  integer,
    supersede_reason text,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX mem_claim_namespace_idx ON mem_claim (namespace);
CREATE INDEX mem_claim_anchors_idx ON mem_claim USING gin (anchors jsonb_path_ops);

CREATE TABLE mem_outcome (
    id             serial PRIMARY KEY,
    namespace      text NOT NULL,
    task_ref       text NOT NULL,
    claim_id       integer REFERENCES mem_claim(id),
    summary        text NOT NULL,
    evidence_ids   integer[] NOT NULL DEFAULT '{}',
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- Tipurile de ancoră v2 care lipsesc din inventarul v1 (SPEC §1.3 permite
-- extinderea DOAR prin migrare cu rând nou în seed + prag definit).
INSERT INTO anchor_type (code, odoo_model, label_ro, resolution_fields,
                         disambiguation_fields, has_chatter, url_template,
                         accept_threshold, review_threshold, active)
VALUES
  ('INITIATIVE', 'pmorg.initiative', 'Inițiativă',
   ARRAY['name','reference'], ARRAY['project_id.name','state'],
   true, '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.85, 0.50, true),
  ('IDENTITY', 'pmorg.identity', 'Identitate',
   ARRAY['name'], ARRAY['identity_kind','company_id.name'],
   false, '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.90, 0.60, true);
