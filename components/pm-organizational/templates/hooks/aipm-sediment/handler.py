"""Hook Hermes `agent:start` → conducta de sedimentare aipm (etapele 3+5).

Identitatea vine STRUCTURAL de la gateway (user_id după allowlist), nu din
text — devine author_key și trece prin vamă (identity_map) în aipm. Poarta
de intimitate rulează în aipm înaintea oricărei persistări. Limită stock
Hermes: textul e trunchiat la 500 de caractere de emiterea hook-ului.

Erorile sunt înghițite (contractul hook-urilor: nu blochează gateway-ul);
redeliverarea e sigură — aipm deduplică pe source_ref.
"""

import json
import os
import urllib.request

AIPM_URL = os.environ.get("AIPM_URL", "http://127.0.0.1:8090").rstrip("/")
AIPM_ENV_FILE = os.environ.get("AIPM_ENV_FILE", "__AIPM_ROOT__/.env")
TIMEOUT = 5


def _token() -> str:
    tok = os.environ.get("AIPM_TOKEN", "")
    if tok:
        return tok
    if os.path.exists(AIPM_ENV_FILE):
        for line in open(AIPM_ENV_FILE):
            if line.startswith("AIPM_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def handle(event_type, context):
    if event_type != "agent:start":
        return
    if (context.get("platform") or "") != "telegram":
        return
    user_id = str(context.get("user_id") or "").strip()
    text = (context.get("message") or "").strip()
    if not user_id or not text:
        return
    payload = {
        "author_key": f"telegram:{user_id}",
        "text": text,
        "chat_id": str(context.get("chat_id") or ""),
        "session_id": str(context.get("session_id") or ""),
    }
    req = urllib.request.Request(
        AIPM_URL + "/api/ingest/gateway",
        method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {_token()}"},
        data=json.dumps(payload, ensure_ascii=False).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read())
            print(f"[aipm-sediment] {body.get('status')} {body.get('source_ref','')}",
                  flush=True)
    except Exception as e:  # niciodată nu blocăm gateway-ul
        print(f"[aipm-sediment] eșuat (neblocant): {e}", flush=True)
