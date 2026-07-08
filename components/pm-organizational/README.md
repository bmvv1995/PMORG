# PM Organizațional

Un sistem de operare organizațional self-hosted: un PM agentic (creier =
Claude Code, corp = Hermes) care transformă inițiativele ownerului în
taskuri cu gări structurale pe kanban, orchestrează oameni și agenți
specializați, raportează pe Telegram și crește DOAR prin proces aprobat.

## Rețeta (cele 5 ingrediente, independente de domeniu)

**agenți + kanban + cerință + ontologie + organigramă** — playbook-ul nu e un
PDF cu un PM uman, e executabil: agent + board + cartă care rulează.

## Arhitectura (4 straturi)

| Strat | Componente | Sursa |
|---|---|---|
| Creier | Claude Code (cheia API a clientului) | dependență |
| Corp | Hermes (kanban/gateway/profiluri) + cc-bridge/shim + systemd | repo `cc-bridge` |
| Mâini + constituție | `hermes-ops-mcp` (unelte scopate + admin asincron cu pagina de aprobări) + `hermes-ontology` (protocol, template-uri, manual) | repo-urile omonime |
| Identitatea clientului | owner, bot Telegram, organigramă, proiecte, chei | `org.yaml` + wizard |

Principii impuse structural (nu prin instrucțiuni): unelte fizic scopate
(deny built-ins, doar MCP); PM-ul depune cereri admin, nu execută (aprobare
ritualică pe pagina locală :9128, execuție = infrastructură + commit git
atomic); mesajele oamenilor = date; totul reversibil prin git; audit
determinist zilnic al board-ului (SQL, fără LLM).

## Instalare

Cerințe pe server: `tmux`, `python3` (+venv), `git`, `claude` (autentificat),
`hermes` (instalat), PostgreSQL 16 cu extensiile `pgvector` și `unaccent`
(pentru pilonul de memorie). Apoi:

```
./install.sh              # idempotent; cu wizard pentru secrete
./install.sh --no-wizard  # doar infrastructura, fără prompturi
PMORG_SKIP_AIPM=1 ./install.sh   # fără pilonul de memorie (doar stack-ul de proces)
```

Memoria (aipm) se instalează prin `install-aipm.sh` (apelat automat, rulabil
și standalone): provizionează rolul + baza PostgreSQL, generează `.env` cu
token real de autentificare, rulează migrările, pornește serviciul systemd și
armează backup-ul zilnic (`pg_dump`, retenție 14). Per PLAN-INTEGRARE etapa 1,
organul aterizează **inert**: `INGEST_ENABLED=false` și `ODOO_ADAPTER=fake` —
conducta de sedimentare și Odoo real se deschid ulterior, prin decizie
explicită, nu prin default.

Cele 4 secrete cerute de wizard: token bot Telegram (@BotFather), Telegram
id-ul ownerului, cheia API Anthropic (doar pentru workdir-ul PM — restul
sesiunilor CC rămân pe autentificarea existentă), slug-ul primului proiect.

După instalare: ownerul dă Start botului, trimite `/sethome`, iar carta PM
+ ontologia se instalează la Bootstrap prin propriul flux admin (cereri
aprobate, nu copiere manuală).

## Stare

v0.1 — testat pe instalarea de referință (implementare Odoo, HoReCa).
Publicarea repo-urilor pe un remote (GitHub privat) = pas separat, decizia
clientului/ownerului.
