-- Jurnalul conversației (PLAN-INTEGRARE etapa 10, necunoscuta 2 / P5).
-- Append-only și în CARANTINĂ: nu e memorie — un rând de aici nu devine
-- niciodată memory_item și nu poate susține un claim. Latura de asistent se
-- jurnalizează imediat (auditul „ce a răspuns memoria săptămâna asta?").
-- Latura de utilizator, verbatim, se activează DOAR după poarta de
-- intimitate (etapa 4) — jurnalul e o conductă nouă de cuvinte umane (P4).

CREATE TABLE chat_turn (
  id         bigserial PRIMARY KEY,
  session_id text NOT NULL,
  role       text NOT NULL CHECK (role IN ('user','assistant')),
  body       text NOT NULL,
  degraded   boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX chat_turn_session_idx ON chat_turn(session_id, id);
CREATE INDEX chat_turn_created_idx ON chat_turn(created_at);

-- append-only impus de schemă, nu de disciplină
CREATE FUNCTION chat_turn_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'chat_turn este append-only (P5): fără UPDATE/DELETE din runtime';
END $$ LANGUAGE plpgsql;

CREATE TRIGGER chat_turn_no_mutation
  BEFORE UPDATE OR DELETE ON chat_turn
  FOR EACH ROW EXECUTE FUNCTION chat_turn_append_only();
