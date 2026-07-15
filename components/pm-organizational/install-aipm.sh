#!/usr/bin/env bash
# Instalarea memoriei (aipm) — PLAN-INTEGRARE etapa 1. Idempotent.
#
# Livrează organul INERT: serviciul rulează, migrat, cu token real, dar
# bucla de ingest e OPRITĂ (INGEST_ENABLED=false) și adaptorul Odoo e pe
# fixtures (ODOO_ADAPTER=fake) până la decizia explicită de a le porni.
# Include backup-ul zilnic al bazei (datoria operațională 1).
#
# Rulabil standalone sau din install.sh. Variabile:
#   PMORG_AIPM   calea către repo-ul care conține pachetul aipm/ (autodetect altfel)
#   PMORG_REPOS  rădăcina repo-urilor (implicit $HOME)
set -euo pipefail

REPOS="${PMORG_REPOS:-$HOME}"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   ✔ %s\n' "$*"; }
warn() { printf '   ⚠ %s\n' "$*"; }

# ------------------------------------------------------------- sursa aipm
say "memoria (aipm): sursa"
AIPM_ROOT=""
for cand in "${PMORG_AIPM:-}" "$REPOS/PMORG" "$REPOS/pmorg" "$REPOS/pm-org" "$REPOS/aipm"; do
  if [ -n "$cand" ] && [ -f "$cand/aipm/requirements.txt" ]; then
    AIPM_ROOT="$cand"
    break
  fi
done
if [ -z "$AIPM_ROOT" ]; then
  warn "nu găsesc pachetul aipm — clonează repo-ul de unificare sau setează PMORG_AIPM=<cale>"
  exit 1
fi
ok "sursa: $AIPM_ROOT"

# ------------------------------------------------------------- dependențe
say "memoria (aipm): dependențe"
MISSING=0
for c in psql pg_isready pg_dump curl; do
  command -v "$c" >/dev/null 2>&1 && ok "$c" || { warn "LIPSĂ: $c (instalează clientul PostgreSQL)"; MISSING=1; }
done
python3 -c "import venv" 2>/dev/null && ok "python3-venv" || { warn "LIPSĂ: python3-venv"; MISSING=1; }
[ "$MISSING" = 1 ] && { echo "Instalează dependențele lipsă și reia."; exit 1; }

# --------------------------------------------------------------- .env
say "memoria (aipm): configurația (.env)"
ENVA="$AIPM_ROOT/.env"
if [ -f "$ENVA" ]; then
  ok ".env există — neatins (idempotent)"
else
  AIPM_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  PG_PASS="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
  cat > "$ENVA" <<EOF
# Generat de install-aipm.sh — $(date +%F). Vezi aipm/.env.example pentru toate opțiunile.
AIPM_AUTH_TOKEN=$AIPM_TOKEN
PG_DSN=postgresql://aipm:$PG_PASS@127.0.0.1:5432/aipm
# fake = fixtures locale; treci pe xmlrpc DOAR după provizionarea userului Odoo (aipm/README §Deploy)
ODOO_ADAPTER=fake
# Memoria se livrează INERTĂ (PLAN-INTEGRARE etapa 1). Deschiderea conductei
# de sedimentare = etapa 5, decizie explicită, nu default.
INGEST_ENABLED=false
# Chitanțe doar din butonul /review (decizia D4, pre-go-live)
RECEIPT_MODE=manual
LLM_API_KEY=
EMBED_API_KEY=
EOF
  chmod 600 "$ENVA"
  ok ".env generat: token real, ingest oprit, adaptor fake explicit"
fi

# extrage componentele DSN pentru pașii următori (shell-quoted, robust la parolă goală)
eval "$(python3 - "$ENVA" <<'PY'
import shlex, sys, urllib.parse
dsn = ""
for line in open(sys.argv[1]):
    if line.startswith("PG_DSN="):
        dsn = line.split("=", 1)[1].strip()
u = urllib.parse.urlparse(dsn)
print(f"PGUSER={shlex.quote(u.username or 'aipm')}")
print(f"PGPASS={shlex.quote(u.password or '')}")
print(f"PGHOST={shlex.quote(u.hostname or '127.0.0.1')}")
print(f"PGPORT={shlex.quote(str(u.port or 5432))}")
print(f"PGDB={shlex.quote((u.path or '/aipm').lstrip('/'))}")
PY
)"

# --------------------------------------------------------- serverul PG + baza
say "memoria (aipm): PostgreSQL"
if ! pg_isready -q -h "$PGHOST" -p "$PGPORT"; then
  warn "PostgreSQL nu răspunde pe $PGHOST:$PGPORT — pornește serverul și reia"
  exit 1
fi
ok "serverul răspunde"

_can_connect() {
  PGPASSWORD="$PGPASS" psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" \
    -qAtc "SELECT 1" >/dev/null 2>&1
}

if _can_connect; then
  ok "rolul și baza există, conexiunea merge"
else
  if sudo -n -u postgres true 2>/dev/null; then
    sudo -n -u postgres psql -p "$PGPORT" -v ON_ERROR_STOP=1 -qc "DO \$\$
      BEGIN
        IF EXISTS (SELECT FROM pg_roles WHERE rolname = '$PGUSER') THEN
          ALTER ROLE $PGUSER LOGIN PASSWORD '$PGPASS';
        ELSE
          CREATE ROLE $PGUSER LOGIN PASSWORD '$PGPASS';
        END IF;
      END \$\$;"
    if ! sudo -n -u postgres psql -p "$PGPORT" -qAtc "SELECT 1 FROM pg_database WHERE datname='$PGDB'" | grep -q 1; then
      sudo -n -u postgres createdb -p "$PGPORT" -O "$PGUSER" "$PGDB"
    fi
    # extensiile cer superuser; migrarea 0001 doar le confirmă (IF NOT EXISTS)
    sudo -n -u postgres psql -p "$PGPORT" -d "$PGDB" -v ON_ERROR_STOP=1 -qc \
      "CREATE EXTENSION IF NOT EXISTS vector;
       CREATE EXTENSION IF NOT EXISTS unaccent;
       CREATE EXTENSION IF NOT EXISTS pgcrypto;"
    _can_connect && ok "rol + bază + extensii provizionate" || { warn "provizionarea a eșuat — verifică manual"; exit 1; }
  else
    warn "nu mă pot conecta ca $PGUSER și nu am sudo către postgres."
    echo "   Rulează ca administrator PostgreSQL, apoi reia:"
    echo "     CREATE ROLE $PGUSER LOGIN PASSWORD '<parola din $ENVA>';"
    echo "     CREATE DATABASE $PGDB OWNER $PGUSER;"
    echo "     \\c $PGDB"
    echo "     CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS unaccent; CREATE EXTENSION IF NOT EXISTS pgcrypto;"
    exit 1
  fi
fi

# ------------------------------------------------------------ venv + migrări
say "memoria (aipm): mediu Python + migrări"
VENV="$AIPM_ROOT/.venv"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -r "$AIPM_ROOT/aipm/requirements.txt"
ok "dependențe instalate ($VENV)"
(cd "$AIPM_ROOT" && "$VENV/bin/python" -m aipm.migrations.migrate)
ok "migrări la zi"

# ------------------------------------------------------------------ systemd
say "memoria (aipm): serviciul + backup-ul zilnic"
BASE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.local/bin"
cp "$BASE/templates/aipm-backup.sh" "$HOME/.local/bin/aipm-backup.sh"
chmod +x "$HOME/.local/bin/aipm-backup.sh"

if systemctl --user show-environment >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  sed "s|__ROOT__|$AIPM_ROOT|g" "$BASE/templates/aipm.service"        > "$HOME/.config/systemd/user/aipm.service"
  sed "s|__ROOT__|$AIPM_ROOT|g" "$BASE/templates/aipm-backup.service" > "$HOME/.config/systemd/user/aipm-backup.service"
  cp "$BASE/templates/aipm-backup.timer" "$HOME/.config/systemd/user/aipm-backup.timer"
  systemctl --user daemon-reload
  systemctl --user enable --now aipm >/dev/null 2>&1 || true
  systemctl --user enable --now aipm-backup.timer >/dev/null 2>&1 || true
  systemctl --user is-active aipm >/dev/null && ok "serviciul aipm activ" \
    || { warn "serviciul aipm NU e activ — journalctl --user -u aipm"; exit 1; }
  systemctl --user is-active aipm-backup.timer >/dev/null && ok "backup zilnic armat (03:30, retenție 14)" \
    || warn "timer-ul de backup NU e activ"
else
  warn "systemd user indisponibil — pornire manuală: cd $AIPM_ROOT && .venv/bin/python -m aipm.main"
  warn "backup manual: ~/.local/bin/aipm-backup.sh $ENVA ~/aipm-backups"
fi

# --------------------------------------------------------------- smoke test
say "memoria (aipm): smoke test"
AIPM_PORT="$(grep '^AIPM_PORT=' "$ENVA" | cut -d= -f2- || true)"
AIPM_PORT="${AIPM_PORT:-8090}"
HEALTH_FILE="$(mktemp)"
HEALTH_OK=0
for _ in 1 2 3 4 5; do
  if curl -fsS "http://127.0.0.1:$AIPM_PORT/api/health" -o "$HEALTH_FILE" 2>/dev/null; then
    HEALTH_OK=1
    break
  fi
  sleep 2
done
if [ "$HEALTH_OK" = 0 ]; then
  warn "serviciul nu răspunde pe /api/health — instalarea NU e completă"
  rm -f "$HEALTH_FILE"
  exit 1
fi
python3 - "$HEALTH_FILE" <<'PY'
import json, sys
h = json.load(open(sys.argv[1]))
problems = []
if not h.get("pg"):
    problems.append(f"PostgreSQL indisponibil din serviciu: {h.get('pg_error')}")
if h.get("ingest_enabled"):
    problems.append("ingestul e PORNIT — livrarea cere memoria inertă (INGEST_ENABLED=false)")
if not h.get("auth_enabled"):
    problems.append("autentificarea e OPRITĂ — AIPM_AUTH_TOKEN gol")
if problems:
    for p in problems:
        print(f"   ⚠ {p}")
    sys.exit(1)
print(f"   ✔ health: pg=da, auth=da, ingest=oprit, adaptor={h.get('adapter_impl')}")
PY
rm -f "$HEALTH_FILE"
CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$AIPM_PORT/api/anchors/types")"
if [ "$CODE" = "401" ]; then
  ok "API-ul refuză cereri fără token (401)"
else
  warn "API-ul a răspuns $CODE fără token — auth NU funcționează"
  exit 1
fi

say "memoria (aipm): GATA — organ instalat, inert"
echo "   UI (prin tunel): http://127.0.0.1:$AIPM_PORT/?token=\$(grep ^AIPM_AUTH_TOKEN $ENVA | cut -d= -f2)"
echo "   Trecerea pe Odoo real (ODOO_ADAPTER=xmlrpc) și pornirea ingestului"
echo "   (INGEST_ENABLED=true) sunt decizii explicite — vezi docs/PLAN-INTEGRARE.md."
