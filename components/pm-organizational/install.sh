#!/usr/bin/env bash
# PM Organizațional — instalator idempotent v0.1
# Sigur de rulat repetat: tot ce există deja e lăsat neatins.
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
REPOS="${PMORG_REPOS:-$HOME}"          # unde stau cele 3 repo-uri sursă
WIZARD=1
[ "${1:-}" = "--no-wizard" ] && WIZARD=0
[ -t 0 ] || WIZARD=0                   # fără TTY nu punem întrebări

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   ✔ %s\n' "$*"; }
warn() { printf '   ⚠ %s\n' "$*"; }

say "dependențe"
MISSING=0
for c in tmux python3 git claude hermes; do
  command -v "$c" >/dev/null 2>&1 && ok "$c" || { warn "LIPSĂ: $c"; MISSING=1; }
done
[ "$MISSING" = 1 ] && { echo "Instalează dependențele lipsă și reia."; exit 1; }

say "repo-urile componente"
for r in cc-bridge hermes-ops-mcp hermes-ontology; do
  [ -d "$REPOS/$r/.git" ] && ok "$r" || { warn "lipsește $REPOS/$r — clonează-l întâi"; exit 1; }
done

say "puntea (symlink-uri + systemd + linger)"
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
for f in cc-bridge cc-mirror-shim; do
  ln -sf "$REPOS/cc-bridge/$f" "$HOME/.local/bin/$f"
done
ok "symlink-uri"
if [ ! -f "$HOME/.config/systemd/user/cc-mirror-shim.service" ]; then
  cp "$REPOS/cc-bridge/cc-mirror-shim.service" "$HOME/.config/systemd/user/"
  systemctl --user daemon-reload
fi
systemctl --user enable --now cc-mirror-shim >/dev/null 2>&1 || true
loginctl enable-linger "$USER" 2>/dev/null || true
systemctl --user is-active cc-mirror-shim >/dev/null && ok "shim activ" || warn "shim NU e activ — vezi journalctl --user -u cc-mirror-shim"

say "reversibilitate: git pe ~/.hermes"
if [ -d "$HOME/.hermes/.git" ]; then
  ok "există deja"
else
  cp "$BASE/templates/hermes.gitignore" "$HOME/.hermes/.gitignore"
  git -C "$HOME/.hermes" init -q
  git -C "$HOME/.hermes" add -A
  git -C "$HOME/.hermes" -c user.name=owner -c user.email=owner@local \
      commit -qm "config: starea initiala a organizatiei" || true
  if git -C "$HOME/.hermes" ls-files | grep -qE '\.env$|auth.*\.json'; then
    warn "SECRETE detectate în git — corectează .gitignore și amendează commit-ul!"
  else
    ok "inițializat, fără secrete versionate"
  fi
fi

say "provider cc-mirror în configul global Hermes"
if grep -q "cc-mirror" "$HOME/.hermes/config.yaml" 2>/dev/null; then
  ok "prezent"
else
  warn "adaugă manual în ~/.hermes/config.yaml:"
  printf '     custom_providers:\n       - name: cc-mirror\n         base_url: http://127.0.0.1:9127/v1\n'
fi

say "workdir-ul PM (mâini legate prin config)"
# aceeași autodetecție ca în install-aipm.sh — pentru __AIPM_ROOT__ din mcp.json
AIPM_ROOT=""
for cand in "${PMORG_AIPM:-}" "$REPOS/PMORG" "$REPOS/pmorg" "$REPOS/pm-org" "$REPOS/aipm"; do
  if [ -n "$cand" ] && [ -f "$cand/aipm/requirements.txt" ]; then
    AIPM_ROOT="$cand"
    break
  fi
done
PMWD="$HOME/cc-sessions/pm"
mkdir -p "$PMWD/.claude"
[ -f "$PMWD/CLAUDE.md" ]              || sed "s|__HOME__|$HOME|g" "$BASE/templates/pm-workdir/CLAUDE.md"     > "$PMWD/CLAUDE.md"
[ -f "$PMWD/.mcp.json" ]              || sed -e "s|__HOME__|$HOME|g" -e "s|__AIPM_ROOT__|${AIPM_ROOT:-$HOME/PMORG}|g" \
                                             "$BASE/templates/pm-workdir/mcp.json"      > "$PMWD/.mcp.json"
[ -f "$PMWD/.claude/settings.json" ]  || cp "$BASE/templates/pm-workdir/settings.json" "$PMWD/.claude/settings.json"
ok "$PMWD"

say "profilul Hermes pm"
if [ -d "$HOME/.hermes/profiles/pm" ]; then
  ok "există deja"
else
  hermes profile create pm --description "PM (dispecer) — mirror al sesiunii CC pm" >/dev/null 2>&1 || true
  CFG="$HOME/.hermes/profiles/pm/config.yaml"
  if [ -f "$CFG" ]; then
    python3 - "$CFG" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p).read()
if "cc-mirror" not in s:
    s = re.sub(r"(?m)^model:.*$", "model:\n  provider: cc-mirror\n  default: pm\n  base_url: http://127.0.0.1:9127/v1", s, count=1)
    open(p, "w").write(s)
PY
    ok "profil creat și legat de cc-mirror"
  else
    warn "profilul nu s-a creat — rulează manual: hermes profile create pm"
  fi
fi

say "auditul determinist al board-ului"
mkdir -p "$HOME/.hermes/scripts"
[ -f "$HOME/.hermes/scripts/audit-board.py" ] || cp "$BASE/templates/audit-board.py" "$HOME/.hermes/scripts/"
ok "script prezent (cron-ul zilnic se instalează după configurarea Telegram: pm cron create \"0 8 * * *\" --name audit-board --no-agent --script audit-board.py --deliver telegram)"

# memoria (aipm) — PLAN-INTEGRARE etapa 1: organul se instalează inert
if [ "${PMORG_SKIP_AIPM:-0}" = 1 ]; then
  say "memoria (aipm)"
  warn "sărită (PMORG_SKIP_AIPM=1) — produsul rulează fără pilonul de memorie"
else
  bash "$BASE/install-aipm.sh"

  say "conducta de sedimentare (hook gateway → memorie) + poarta de intimitate"
  PMPROF="$HOME/.hermes/profiles/pm"
  mkdir -p "$PMPROF/hooks/aipm-sediment"
  cp "$BASE/templates/hooks/aipm-sediment/HOOK.yaml" "$PMPROF/hooks/aipm-sediment/"
  sed "s|__AIPM_ROOT__|${AIPM_ROOT:-$HOME/PMORG}|g" \
      "$BASE/templates/hooks/aipm-sediment/handler.py" > "$PMPROF/hooks/aipm-sediment/handler.py"
  ok "hook aipm-sediment instalat (activ la restartul gateway-ului)"
  if [ ! -f "$PMPROF/privacy-denylist.txt" ]; then
    cp "$BASE/templates/privacy-denylist.txt" "$PMPROF/privacy-denylist.txt"
    ok "lista de intimitate creată (completeaz-o: $PMPROF/privacy-denylist.txt)"
  fi
  AIPM_ENV="${AIPM_ROOT:-$HOME/PMORG}/.env"
  if [ -f "$AIPM_ENV" ] && ! grep -q "^PRIVACY_DENYLIST_FILE=" "$AIPM_ENV"; then
    printf 'PRIVACY_DENYLIST_FILE=%s\n' "$PMPROF/privacy-denylist.txt" >> "$AIPM_ENV"
    ok "PRIVACY_DENYLIST_FILE setat în .env-ul aipm"
  fi
  echo "   Conducta rămâne ÎNCHISĂ până la decizia explicită: INGEST_ENABLED=true"
  echo "   în $AIPM_ENV + restart aipm (PLAN-INTEGRARE etapa 5)."
fi

if [ "$WIZARD" = 1 ]; then
  say "wizard — cele 4 secrete (Enter = sari peste)"
  ENVF="$HOME/.hermes/profiles/pm/.env"
  touch "$ENVF"; chmod 600 "$ENVF"
  if ! grep -q TELEGRAM_BOT_TOKEN "$ENVF"; then
    read -r -p "   Token bot Telegram (@BotFather): " TOK
    [ -n "$TOK" ] && printf 'TELEGRAM_BOT_TOKEN=%s\n' "$TOK" >> "$ENVF" && ok "token salvat"
  fi
  if ! grep -q TELEGRAM_ALLOWED_USERS "$ENVF"; then
    read -r -p "   Telegram id-ul ownerului (numeric): " OID
    [ -n "$OID" ] && printf 'TELEGRAM_ALLOWED_USERS=%s\n' "$OID" >> "$ENVF" && ok "allowlist setat"
  fi
  if ! grep -q ANTHROPIC_API_KEY "$PMWD/.claude/settings.json"; then
    read -r -p "   Cheia API Anthropic (doar pt. PM): " KEY
    if [ -n "$KEY" ]; then
      python3 - "$PMWD/.claude/settings.json" "$KEY" <<'PY'
import json, sys
p, key = sys.argv[1], sys.argv[2]
cfg = json.load(open(p))
cfg.setdefault("env", {})["ANTHROPIC_API_KEY"] = key
json.dump(cfg, open(p, "w"), indent=2)
PY
      ok "PM-ul va rula pe API billing (restul sesiunilor CC neatinse)"
    fi
  fi
  read -r -p "   Slug-ul primului proiect (ex. implementare-odoo): " SLUG
  [ -n "$SLUG" ] && hermes kanban boards create "$SLUG" >/dev/null 2>&1 && ok "board $SLUG creat"
  if grep -q TELEGRAM_BOT_TOKEN "$ENVF"; then
    HERMES_PROFILE=pm hermes gateway install >/dev/null 2>&1 || true
    ok "gateway instalat — ownerul: Start pe bot + /sethome"
  fi
else
  say "wizard sărit (--no-wizard sau fără TTY) — secretele se pun ulterior"
fi

say "GATA"
echo "   Pagina de aprobări: ssh -L 9128:127.0.0.1:9128 <server>, apoi"
echo "   http://localhost:9128/admin?token=\$(cat ~/.cc-bridge/admin.token)"
echo "   Următorul pas organizațional: Bootstrap (carta PM + ontologia, prin fluxul admin)."
