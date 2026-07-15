-- Vama (INTENT: joncțiunea unică) — PLAN-INTEGRARE etapa 2, decizia D1.
-- Corespondența dintre lumea canalelor (oameni pe Telegram, proiecte pe board-uri)
-- și lumea Odoo. Regimul de scriere e cel al inventarului de ancore (SPEC §1.1):
-- rândurile intră DOAR prin migrare nouă (cu approved_by), niciodată din runtime —
-- runtime-ul doar citește. O cheie absentă = gol de cunoaștere înregistrat
-- (external_entity), niciodată o identitate inventată (P1/P2).

-- Axa identitate: cine e PARTE la conversație (autorul) — identitate certă.
-- Persoanele doar POMENITE în text rămân pe rezoluția cu candidați + review (D1).
CREATE TABLE identity_map (
  channel         text NOT NULL CHECK (channel IN ('telegram')),
  channel_id      text NOT NULL,
  partner_res_id  integer,           -- res.partner → alimentează memory_item.author_ref
  employee_res_id integer,           -- hr.employee → ancora owner a angajamentelor proprii
  display_name    text NOT NULL,
  approved_by     text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (channel, channel_id),
  CHECK (partner_res_id IS NOT NULL OR employee_res_id IS NOT NULL)
);

-- Axa proiect: board-ul Hermes → înregistrarea project.project din Odoo
-- (condiția practică din INTENT: proiectele PM au ancoră și chatter).
CREATE TABLE project_map (
  board_slug     text PRIMARY KEY,
  project_res_id integer NOT NULL,
  approved_by    text NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);
