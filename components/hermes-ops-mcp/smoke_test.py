#!/usr/bin/env python3
"""Test de fum pentru hermes-ops-mcp: protocol + ciclu de viață real pe board.

Rulează serverul ca subproces stdio și verifică:
  initialize → tools/list → create → comment → link/gară → show → complete
  → arhivare (curățenie) → boards/send/cron read-only.
"""
import json
import subprocess
import sys

SERVER = ["/usr/bin/python3", "/home/vscode/hermes-ops-mcp/server.py"]

proc = subprocess.Popen(SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        text=True, bufsize=1)
_id = 0


def rpc(method, params=None):
    global _id
    _id += 1
    proc.stdin.write(json.dumps(
        {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}) + "\n")
    proc.stdin.flush()
    reply = json.loads(proc.stdout.readline())
    assert reply["id"] == _id, reply
    if "error" in reply:
        raise RuntimeError(reply["error"])
    return reply["result"]


def call(name, **args):
    r = rpc("tools/call", {"name": name, "arguments": args})
    text = r["content"][0]["text"]
    if r.get("isError"):
        raise RuntimeError(f"{name}: {text}")
    return text


def ok(label, detail=""):
    print(f"  ✔ {label}" + (f" — {detail}" if detail else ""))


# 1. protocol
init = rpc("initialize", {"protocolVersion": "2025-03-26",
                          "clientInfo": {"name": "smoke", "version": "0"},
                          "capabilities": {}})
assert init["serverInfo"]["name"] == "hermes-ops"
ok("initialize", init["serverInfo"]["version"])

tools = rpc("tools/list")["tools"]
names = {t["name"] for t in tools}
ok("tools/list", f"{len(tools)} unelte")

# 2. validare argumente obligatorii (regula ARTEFACT: complete fără result)
r = rpc("tools/call", {"name": "kanban_complete", "arguments": {"task_id": "t0"}})
assert r["isError"] and "result" in r["content"][0]["text"]
ok("complete fără artefact → refuzat")

# 3. ciclu de viață real
created = json.loads(call("kanban_create",
                          title="SMOKE: validează hermes-ops-mcp",
                          body="Task de test al infrastructurii. GATA = serverul trece testul."))
tid = created.get("id") or created.get("task_id") or created.get("task", {}).get("id")
assert tid, created
ok("kanban_create", f"task {tid}")

gate = json.loads(call("kanban_create",
                       title="SMOKE: gară aval (se naște blocată)",
                       blocked=True, parents=[str(tid)]))
gid = gate.get("id") or gate.get("task_id") or gate.get("task", {}).get("id")
ok("kanban_create blocked+parent", f"task {gid}")

call("kanban_comment", task_id=str(tid),
     text="ARTEFACT: rezultat-test — protocolul MCP și wrapperele CLI funcționează.")
ok("kanban_comment")

shown = call("kanban_show", task_id=str(tid))
assert "ARTEFACT" in shown
ok("kanban_show", "artefactul e vizibil în comments")

call("kanban_complete", task_id=str(tid),
     result="ARTEFACT: rezultat-test — smoke test trecut integral.")
ok("kanban_complete")

# 4. read-only pe restul suprafeței
assert "default" in call("boards_list")
ok("boards_list")
call("kanban_stats")
ok("kanban_stats")
call("kanban_assignees")
ok("kanban_assignees")
call("send_targets")
ok("send_targets")
call("cron_list")
ok("cron_list")

# 5. curățenie: arhivează taskurile de test
call("kanban_archive", task_ids=[str(tid), str(gid)])
ok("kanban_archive", "board curat")

proc.stdin.close()
proc.wait(timeout=10)
print(f"\nTOATE TESTELE AU TRECUT ({len(names)} unelte expuse)")
