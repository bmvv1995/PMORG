-- Închiderea angajamentelor (PLAN-INTEGRARE etapa 8, decizia D3).
--
-- Felia C (automată, P3-pur): definiția „înregistrare Odoo închisă" per tip de
-- ancoră — closed_field/closed_values pe anchor_type, guvernate PRIN MIGRARE
-- (SPEC §1.1), niciodată din runtime. Starea se derivă LIVE la fiecare raport:
-- nu se stochează nimic, deci redeschiderea în Odoo reactivează automat.
--
-- Felia A (umană): omul marchează 'resolved' din ecranul de verificare —
-- coloanele de audit țin P5 (cine, când).

ALTER TABLE anchor_type
  ADD COLUMN closed_field  text,
  ADD COLUMN closed_values text[];

UPDATE anchor_type SET closed_field='state', closed_values=ARRAY['1_done','1_canceled']
 WHERE code='TASK';
UPDATE anchor_type SET closed_field='state', closed_values=ARRAY['done','cancel']
 WHERE code='PURCHASE_ORDER';
UPDATE anchor_type SET closed_field='state', closed_values=ARRAY['done','cancel']
 WHERE code='SALE_ORDER';
-- LEAD/PROJECT/PARTNER/...: fără definiție de închidere în v1 (closed_field NULL).

ALTER TABLE memory_item
  ADD COLUMN resolved_by text,
  ADD COLUMN resolved_at timestamptz;
