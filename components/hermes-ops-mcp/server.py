#!/usr/bin/env python3
"""hermes-ops-mcp — suprafața de unelte a PM-ului peste CLI-ul Hermes.

Server MCP (stdio, JSON-RPC pe linii) fără nicio dependență externă.
Fiecare tool = wrapper determinist peste o comandă `hermes` (subprocess,
fără LLM, fără shell). Suprafața e FIXĂ la deploy: extinderea ei = commit
git, deci trece prin procesul cu gări al organizației.

Identitatea (author/created-by) e legată de server prin HERMES_OPS_AUTHOR
(implicit: pm) — clientul nu o poate falsifica per apel.
"""

import json
import os
import subprocess
import sys

HERMES = os.environ.get("HERMES_BIN", "/home/vscode/.local/bin/hermes")
AUTHOR = os.environ.get("HERMES_OPS_AUTHOR", "pm")
TIMEOUT = int(os.environ.get("HERMES_OPS_TIMEOUT", "120"))
VERSION = "0.1.0"

# ---------------------------------------------------------------- executare

def _hermes(args):
    try:
        r = subprocess.run(
            [HERMES] + args,
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"[timeout după {TIMEOUT}s] hermes {' '.join(args)}", True
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    text = out if out else ""
    if err:
        text = (text + "\n[stderr] " + err).strip()
    if r.returncode != 0:
        return f"[exit {r.returncode}] {text}", True
    return text or "(ok)", False


def _kanban(sub, board=None):
    pre = ["kanban"]
    if board:
        pre += ["--board", board]
    return _hermes(pre + sub)


# ------------------------------------------------------------------- tools
# Fiecare intrare: (descriere, schema proprietăți, listă câmpuri obligatorii,
# handler(argumente) -> (text, is_error)).

def _s(desc):
    return {"type": "string", "description": desc}


BOARD = _s("Board slug (opțional; implicit board-ul curent)")

TOOLS = {}


def tool(name, description, properties, required, handler):
    TOOLS[name] = {
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
        "handler": handler,
    }


# --- kanban ---

tool(
    "kanban_create",
    "Creează un task pe board. `parents` = id-urile gărilor din amonte "
    "(taskul depinde structural de ele). `blocked=true` → taskul se naște "
    "blocat (modelul standard de gară: avalul așteaptă amontele). "
    "created-by e setat automat la identitatea serverului.",
    {
        "title": _s("Titlul: <verb la imperativ> <obiect> [<context>]"),
        "body": _s("Context: de ce există taskul + definiția lui GATA (artefactul cerut)"),
        "assignee": _s("Profilul/agentul asignat (vezi kanban_assignees)"),
        "parents": {"type": "array", "items": {"type": "string"},
                    "description": "Id-urile taskurilor din amonte (gările)"},
        "blocked": {"type": "boolean", "description": "Se naște blocat (gară)"},
        "priority": {"type": "integer", "description": "Prioritate (tiebreaker)"},
        "board": BOARD,
    },
    ["title"],
    lambda a: _kanban(
        ["create", a["title"]]
        + (["--body", a["body"]] if a.get("body") else [])
        + (["--assignee", a["assignee"]] if a.get("assignee") else [])
        + [x for p in (a.get("parents") or []) for x in ("--parent", p)]
        + (["--initial-status", "blocked"] if a.get("blocked") else [])
        + (["--priority", str(a["priority"])] if a.get("priority") is not None else [])
        + ["--created-by", AUTHOR, "--json"],
        a.get("board"),
    ),
)

tool(
    "kanban_list",
    "Listează taskurile board-ului (JSON). Filtrare opțională pe status/assignee.",
    {
        "status": {"type": "string",
                   "enum": ["triage", "todo", "ready", "running", "review",
                            "blocked", "scheduled", "done", "archived"],
                   "description": "Filtru status"},
        "assignee": _s("Filtru assignee (profil)"),
        "board": BOARD,
    },
    [],
    lambda a: _kanban(
        ["list", "--json"]
        + (["--status", a["status"]] if a.get("status") else [])
        + (["--assignee", a["assignee"]] if a.get("assignee") else []),
        a.get("board"),
    ),
)

tool(
    "kanban_show",
    "Arată un task complet: body, comments (aici sunt ARTEFACTELE), events, runs.",
    {"task_id": _s("Id-ul taskului"), "board": BOARD},
    ["task_id"],
    lambda a: _kanban(["show", a["task_id"], "--json"], a.get("board")),
)

tool(
    "kanban_link",
    "Adaugă dependența parent→child (gara: child nu devine ready până parent nu e done).",
    {"parent_id": _s("Taskul din amonte"), "child_id": _s("Taskul din aval"), "board": BOARD},
    ["parent_id", "child_id"],
    lambda a: _kanban(["link", a["parent_id"], a["child_id"]], a.get("board")),
)

tool(
    "kanban_comment",
    "Adaugă un comment pe task (protocolul inter-agent: constatări, `@destinatar:`, "
    "`ARTEFACT: <tip> — <conținut>`, `ESCALADARE: <motiv>`). Author = identitatea serverului.",
    {"task_id": _s("Id-ul taskului"), "text": _s("Corpul comentariului"), "board": BOARD},
    ["task_id", "text"],
    lambda a: _kanban(["comment", a["task_id"], a["text"], "--author", AUTHOR], a.get("board")),
)

tool(
    "kanban_assign",
    "Asignează (sau re-asignează) un task unui profil. 'none' = dezasignare.",
    {"task_id": _s("Id-ul taskului"), "profile": _s("Numele profilului sau 'none'"), "board": BOARD},
    ["task_id", "profile"],
    lambda a: _kanban(["assign", a["task_id"], a["profile"]], a.get("board")),
)

tool(
    "kanban_complete",
    "Închide un task. `result` e OBLIGATORIU — regula ARTEFACT: un task fără "
    "artefact depus nu se închide. Rezumatul devine context pentru taskurile din aval.",
    {
        "task_id": _s("Id-ul taskului"),
        "result": _s("ARTEFACT: <tip> — <conținut sau referință> (obligatoriu)"),
        "board": BOARD,
    },
    ["task_id", "result"],
    lambda a: _kanban(["complete", a["task_id"], "--result", a["result"]], a.get("board")),
)

tool(
    "kanban_block",
    "Blochează un task cu motiv (motivul devine comment). `kind`: dependency "
    "(așteaptă alte taskuri), needs_input (așteaptă un om), capability, transient.",
    {
        "task_id": _s("Id-ul taskului"),
        "reason": _s("Motivul blocării"),
        "kind": {"type": "string",
                 "enum": ["capability", "dependency", "needs_input", "transient"],
                 "description": "Tipul blocajului"},
        "board": BOARD,
    },
    ["task_id", "reason"],
    lambda a: _kanban(
        ["block", a["task_id"], a["reason"]]
        + (["--kind", a["kind"]] if a.get("kind") else []),
        a.get("board"),
    ),
)

tool(
    "kanban_unblock",
    "Deblochează un task (motivul se înregistrează ca comment).",
    {"task_id": _s("Id-ul taskului"), "reason": _s("Motivul deblocării"), "board": BOARD},
    ["task_id"],
    lambda a: _kanban(
        ["unblock", a["task_id"]]
        + (["--reason", a["reason"]] if a.get("reason") else []),
        a.get("board"),
    ),
)

tool(
    "kanban_archive",
    "Arhivează taskuri închise/abandonate (igiena board-ului).",
    {"task_ids": {"type": "array", "items": {"type": "string"},
                  "description": "Id-urile taskurilor"}, "board": BOARD},
    ["task_ids"],
    lambda a: _kanban(["archive"] + list(a["task_ids"]), a.get("board")),
)

tool(
    "kanban_stats",
    "Statistici board: per-status, per-assignee, vârsta celui mai vechi task ready.",
    {"board": BOARD},
    [],
    lambda a: _kanban(["stats"], a.get("board")),
)

tool(
    "kanban_assignees",
    "Listează profilurile cunoscute + numărul de taskuri per profil (harta de rutare).",
    {"board": BOARD},
    [],
    lambda a: _kanban(["assignees"], a.get("board")),
)

tool(
    "boards_list",
    "Listează board-urile (un board per proiect/flux de lucru).",
    {},
    [],
    lambda a: _kanban(["boards", "list"]),
)

tool(
    "board_create",
    "Creează un board nou (un proiect/flux de lucru nou).",
    {
        "slug": _s("Slug kebab-case, ex. implementare-odoo"),
        "name": _s("Nume afișat"),
        "description": _s("Descriere"),
    },
    ["slug"],
    lambda a: _kanban(
        ["boards", "create", a["slug"]]
        + (["--name", a["name"]] if a.get("name") else [])
        + (["--description", a["description"]] if a.get("description") else []),
    ),
)

# --- administrare (asincron, HIL) ---
# PM-ul NU are putere admin directă: depune cereri motivate; ownerul decide
# ritualic pe pagina de aprobări (:9128/admin), iar EXECUTORUL (shim,
# determinist) aplică acțiunea + commit git. PM-ul nu așteaptă — dispecerizează.

ADMIN_QUEUE = "/home/vscode/.cc-bridge/admin-queue"

import time as _time


def _admin_request(a):
    os.makedirs(ADMIN_QUEUE, exist_ok=True)
    existing = [f for f in os.listdir(ADMIN_QUEUE) if f.endswith(".json")]
    rid = len(existing) + 1
    req = {"id": rid, "action": a["action"], "params": a.get("params") or {},
           "rationale": a["rationale"], "status": "pending",
           "requested_by": AUTHOR, "requested_at": _time.time()}
    with open(os.path.join(ADMIN_QUEUE, f"req-{rid:04d}.json"), "w") as f:
        json.dump(req, f, ensure_ascii=False, indent=1)
    subprocess.run(
        [HERMES, "send", "-t", "telegram", "-q",
         f"🔐 Cerere admin #{rid}: {a['action']}\n"
         f"Motivație (PM): {a['rationale'][:300]}\n"
         f"Decizia — doar pe pagina de aprobări (port 9128)."],
        capture_output=True, text=True, timeout=60)
    return (f"Cerere admin #{rid} înregistrată ({a['action']}); ownerul a fost "
            f"notificat. Execuția se face DOAR după aprobarea lui — continuă-ți "
            f"munca, verifică mai târziu cu admin_list."), False


tool(
    "admin_request",
    "Depune o cerere de administrare a structurii Hermes (agent nou, cartă, "
    "allowlist...). NU execută nimic: ownerul aprobă ritualic pe pagina de "
    "aprobări, apoi executorul infrastructurii aplică acțiunea cu commit git. "
    "Nu bloca dispeceratul așteptând — cererea e asincronă. "
    "Acțiuni: profile_create {name, clone_from?, description?}, "
    "soul_write {profile, content}, ontology_install {profile}, "
    "allowlist_add {telegram_id}, gateway_restart {}.",
    {
        "action": {"type": "string",
                   "enum": ["profile_create", "soul_write", "ontology_install",
                            "allowlist_add", "gateway_restart"],
                   "description": "Tipul acțiunii cerute"},
        "params": {"type": "object",
                   "description": "Parametrii acțiunii (vezi descrierea per acțiune)"},
        "rationale": _s("Motivația cererii — obligatorie; ownerul o citește la aprobare. "
                        "Referențiază taskul-nevoie de pe board dacă există."),
    },
    ["action", "rationale"],
    _admin_request,
)

tool(
    "admin_list",
    "Listează cererile de administrare și statusul lor (pending/executed/denied/failed).",
    {},
    [],
    lambda a: (json.dumps(
        [json.load(open(os.path.join(ADMIN_QUEUE, f)))
         for f in sorted(os.listdir(ADMIN_QUEUE)) if f.endswith(".json")]
        if os.path.isdir(ADMIN_QUEUE) else [], ensure_ascii=False, indent=1), False),
)

# --- send ---

tool(
    "send_message",
    "Trimite un mesaj pe o platformă configurată (fără LLM). Target: "
    "'telegram', 'telegram:<chat_id>', 'discord:#canal' etc. "
    "Folosit pentru rapoarte, notificări, escaladări.",
    {
        "target": _s("Ținta: platform sau platform:chat_id"),
        "message": _s("Textul mesajului"),
        "subject": _s("Linie de subiect (opțional)"),
    },
    ["target", "message"],
    lambda a: _hermes(
        ["send", "-t", a["target"]]
        + (["-s", a["subject"]] if a.get("subject") else [])
        + [a["message"]],
    ),
)

tool(
    "send_targets",
    "Listează țintele de mesagerie disponibile.",
    {},
    [],
    lambda a: _hermes(["send", "--list"]),
)

# --- cron ---

tool(
    "cron_list",
    "Listează joburile programate.",
    {},
    [],
    lambda a: _hermes(["cron", "list"]),
)

tool(
    "cron_create",
    "Creează un job programat (ex. raport zilnic, nudge anti-stagnare). "
    "Schedule: '30m', 'every 2h' sau cron '0 9 * * *'.",
    {
        "schedule": _s("Programarea: '30m', 'every 2h', '0 9 * * *'"),
        "prompt": _s("Instrucțiunea self-contained a jobului"),
        "name": _s("Nume uman al jobului"),
        "deliver": _s("Ținta livrării: origin, local, telegram, platform:chat_id"),
    },
    ["schedule", "prompt"],
    lambda a: _hermes(
        ["cron", "create", a["schedule"], a["prompt"]]
        + (["--name", a["name"]] if a.get("name") else [])
        + (["--deliver", a["deliver"]] if a.get("deliver") else []),
    ),
)

tool(
    "cron_remove",
    "Șterge un job programat.",
    {"job_id": _s("Id-ul jobului (din cron_list)")},
    ["job_id"],
    lambda a: _hermes(["cron", "remove", a["job_id"]]),
)


# ---------------------------------------------------------------- protocol

def handle(msg):
    method = msg.get("method")
    params = msg.get("params") or {}

    if method == "initialize":
        return {
            "protocolVersion": params.get("protocolVersion", "2025-03-26"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "hermes-ops", "version": VERSION},
        }

    if method == "ping":
        return {}

    if method == "tools/list":
        return {
            "tools": [
                {"name": n, "description": t["description"],
                 "inputSchema": t["inputSchema"]}
                for n, t in TOOLS.items()
            ]
        }

    if method == "tools/call":
        name = params.get("name")
        t = TOOLS.get(name)
        if t is None:
            return {"content": [{"type": "text", "text": f"tool necunoscut: {name}"}],
                    "isError": True}
        args = params.get("arguments") or {}
        missing = [r for r in t["inputSchema"]["required"] if not args.get(r)]
        if missing:
            return {"content": [{"type": "text",
                                 "text": f"argumente obligatorii lipsă: {', '.join(missing)}"}],
                    "isError": True}
        try:
            text, is_err = t["handler"](args)
        except Exception as e:  # apărare: o unealtă căzută nu omoară serverul
            text, is_err = f"[eroare internă] {e!r}", True
        return {"content": [{"type": "text", "text": text}], "isError": is_err}

    raise LookupError(method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:
            continue  # notificare — nu cere răspuns
        try:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
        except LookupError as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"],
                     "error": {"code": -32601, "message": f"method not found: {e}"}}
        except Exception as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"],
                     "error": {"code": -32603, "message": repr(e)}}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
