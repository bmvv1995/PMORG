-- Conducta de sedimentare de la gateway (PLAN-INTEGRARE etapele 3+5).
-- 'gateway' = mesajele oamenilor de pe canale (Telegram), livrate de hook-ul
-- stock al gateway-ului Hermes, cu identitatea REALĂ (post-allowlist) ca
-- author_key prin vamă. 'privacy_blocked' = refuzul porții de intimitate,
-- consemnat FĂRĂ conținut (P4/P5).

ALTER TABLE memory_item DROP CONSTRAINT memory_item_source_type_check;
ALTER TABLE memory_item ADD CONSTRAINT memory_item_source_type_check
  CHECK (source_type IN ('chatter','chat','gateway'));

ALTER TABLE ingest_log DROP CONSTRAINT ingest_log_status_check;
ALTER TABLE ingest_log ADD CONSTRAINT ingest_log_status_check
  CHECK (status IN ('done','extract_failed','no_items','retrying','error','privacy_blocked'));
