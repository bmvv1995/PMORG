"""Runner de migrații — SQL numerotat, forward-only (plan §E).

Refuză să ruleze dacă un fișier deja aplicat s-a modificat (hash).
Utilizare: python -m aipm.migrations.migrate [dsn]
"""

import hashlib
import pathlib
import sys

import psycopg

MIGRATIONS_DIR = pathlib.Path(__file__).parent


def run(dsn: str) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migration (
                 filename text PRIMARY KEY, hash text NOT NULL,
                 applied_at timestamptz NOT NULL DEFAULT now())"""
        )
        conn.commit()
        done = {
            r[0]: r[1]
            for r in conn.execute("SELECT filename, hash FROM schema_migration").fetchall()
        }
        for path in sorted(MIGRATIONS_DIR.glob("[0-9]*.sql")):
            sql = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            if path.name in done:
                if done[path.name] != digest:
                    raise RuntimeError(f"migrația aplicată {path.name} a fost modificată — interzis (forward-only)")
                continue
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migration (filename, hash) VALUES (%s, %s)",
                    (path.name, digest),
                )
            applied.append(path.name)
    return applied


if __name__ == "__main__":
    from aipm import config

    dsn = sys.argv[1] if len(sys.argv) > 1 else config.PG_DSN
    for name in run(dsn):
        print(f"applied: {name}")
    print("migrations up to date")
