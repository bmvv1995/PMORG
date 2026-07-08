# hermes-ops-mcp

Suprafața de unelte a PM-ului: un server MCP (stdio) care expune primitivele
Hermes — kanban, send, cron — ca unelte scopate pentru o instanță Claude Code.

## De ce există

Arhitectura PM-on-CC: creierul și harness-ul PM-ului sunt Claude Code pe API
billing (cache eficient, compaction nativă), iar **mâinile** sunt exact acest
server. PM-ului i se dezactivează toate uneltele built-in (fără Bash, Write,
Edit) și i se permite doar `hermes-ops`. Rezultatul:

- **Limita e fizică, nu instrucțiune** — suprafața de unelte e fixată la
  deploy; PM-ul nu poate face decât ce există aici.
- **La runtime e doar dispecer** — extinderea suprafeței = modificare de cod
  = commit git = trece prin procesul cu gări din protocolul organizației.
- **Identitate legată** — `author`/`created-by` vin din `HERMES_OPS_AUTHOR`
  (implicit `pm`), nu din apel; PM-ul nu poate semna drept altcineva.
- **Regula ARTEFACT în structură** — `kanban_complete` refuză închiderea
  fără `result`.

## Design

- **Zero dependențe**: doar stdlib Python (pe server nu există python3-venv,
  și nici nu vrem drift de dependențe pe o piesă de temelie). Protocolul MCP
  stdio = JSON-RPC pe linii — implementat direct în `server.py`.
- Fiecare tool = `subprocess` pe binarul `hermes` (argv, fără shell, timeout).
  Niciun LLM în interior — wrapper determinist.

## Uneltele (19)

- **kanban**: create (cu `parents` + `blocked` = gările structurale), list,
  show, link, comment, assign, complete, block, unblock, archive, stats,
  assignees, boards_list, board_create
- **send**: send_message, send_targets
- **cron**: cron_list, cron_create, cron_remove

## Instalare în profilul PM (la Bootstrap)

În workdir-ul instanței CC a PM-ului, `.mcp.json`:

```json
{
  "mcpServers": {
    "hermes-ops": {
      "command": "/usr/bin/python3",
      "args": ["/home/vscode/hermes-ops-mcp/server.py"],
      "env": { "HERMES_OPS_AUTHOR": "pm" }
    }
  }
}
```

plus dezactivarea uneltelor built-in în `.claude/settings.json` al acelui
workdir (deny pe Bash/Write/Edit/WebFetch etc., allow pe `mcp__hermes-ops__*`).

## Test

```
python3 /home/vscode/hermes-ops-mcp/smoke_test.py
```

Exersează protocolul + un ciclu de viață complet pe board (taskurile de test
se arhivează singure la final).

## Variabile de mediu

| Variabilă | Implicit | Rol |
|---|---|---|
| `HERMES_BIN` | `/home/vscode/.local/bin/hermes` | binarul înfășurat |
| `HERMES_OPS_AUTHOR` | `pm` | identitatea semnăturilor |
| `HERMES_OPS_TIMEOUT` | `120` | timeout per comandă (s) |
