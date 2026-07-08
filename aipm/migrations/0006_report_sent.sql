-- Jurnalul de trimitere al livrării proactive (PLAN-INTEGRARE etapa 9).
-- Idempotența digestului: un element o dată livrat nu se retrimite zilnic
-- (anti nag-spam); cheia elementului include discriminantul de stare
-- (ex. due_at), deci schimbarea termenului îl readuce legitim în digest.
-- Generalizarea tiparului external_entity_status (P5: trimisul e consemnat).

CREATE TABLE report_sent (
  report_code text NOT NULL,
  item_key    text NOT NULL,
  sent_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (report_code, item_key)
);
