-- Seed v1 — valorile EXACTE din SPEC §1.3 (inventarul de ancore),
-- §1.5 (matricea kind × subject) și R-001 (poarta de scriere, vizibilă).
-- Modificarea acestor rânduri = migrare nouă, niciodată UPDATE la runtime (SPEC §1.1).

INSERT INTO anchor_type (code, odoo_model, label_ro, resolution_fields, disambiguation_fields, has_chatter, url_template, accept_threshold, review_threshold) VALUES
  ('COMPANY',        'res.company',      'Compania',          ARRAY['name'],                ARRAY[]::text[],                                                        false, '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.95, 0.70),
  ('PROJECT',        'project.project',  'Proiect',           ARRAY['name'],                ARRAY['user_id.name'],                                                  true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.85, 0.50),
  ('TASK',           'project.task',     'Task',              ARRAY['name'],                ARRAY['project_id.name','user_ids.name','date_deadline'],               true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.85, 0.50),
  ('PARTNER',        'res.partner',      'Partener',          ARRAY['name','email','ref'],  ARRAY['city','is_company','supplier_rank','customer_rank'],             true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.85, 0.50),
  ('EMPLOYEE',       'hr.employee',      'Angajat',           ARRAY['name','work_email'],   ARRAY['job_title','department_id.name'],                                true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.90, 0.60),
  ('PURCHASE_ORDER', 'purchase.order',   'Comandă achiziție', ARRAY['name','partner_ref'],  ARRAY['partner_id.name','date_order','state'],                          true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.90, 0.60),
  ('SALE_ORDER',     'sale.order',       'Comandă vânzare',   ARRAY['name'],                ARRAY['partner_id.name','date_order','state'],                          true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.90, 0.60),
  ('LEAD',           'crm.lead',         'Oportunitate',      ARRAY['name'],                ARRAY['partner_name','expected_revenue'],                               true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.85, 0.50),
  ('PRODUCT',        'product.template', 'Produs',            ARRAY['name','default_code'], ARRAY['categ_id.name','list_price'],                                    true,  '{base_url}/odoo/{odoo_model}/{odoo_res_id}', 0.85, 0.50);

-- SPEC §1.5 — matricea kind × subject (constrângere seedată, nu convenție)
INSERT INTO kind_subject_allowed (kind, anchor_code) VALUES
  ('decision','PROJECT'), ('decision','TASK'), ('decision','PURCHASE_ORDER'),
  ('decision','SALE_ORDER'), ('decision','LEAD'), ('decision','PRODUCT'), ('decision','COMPANY'),
  ('commitment','TASK'), ('commitment','PROJECT'), ('commitment','LEAD'),
  ('commitment','PURCHASE_ORDER'), ('commitment','SALE_ORDER'), ('commitment','PARTNER'),
  ('observation','COMPANY'), ('observation','PROJECT'), ('observation','TASK'),
  ('observation','PARTNER'), ('observation','EMPLOYEE'), ('observation','PURCHASE_ORDER'),
  ('observation','SALE_ORDER'), ('observation','LEAD'), ('observation','PRODUCT'),
  ('open_question','PROJECT'), ('open_question','TASK'), ('open_question','PURCHASE_ORDER'),
  ('open_question','LEAD'), ('open_question','PARTNER'), ('open_question','COMPANY'),
  ('rule_candidate','COMPANY'), ('rule_candidate','PROJECT');

INSERT INTO rule (code, body_ro, approved_by) VALUES
  ('R-001', 'Singura scriere Odoo permisă în v1: message_post (chitanța). Orice altă metodă de scriere este respinsă în codul adaptorului (WriteGateViolation).', 'owner');
