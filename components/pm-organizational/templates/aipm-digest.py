#!/usr/bin/env python3
"""Digestul memoriei pe Telegram — PLAN-INTEGRARE etapa 9 (INTENT fluxul 3).

Rulat de ceasul Hermes, fără agent (tiparul audit-board.py): cere digestul
determinist de la aipm și îl tipărește; Hermes livrează ce s-a tipărit.
Nimic tipărit = nimic de livrat (elementele deja trimise nu se repetă).

Instalare (după configurarea Telegram):
  pm cron create "0 8 * * *" --name aipm-digest --no-agent \
      --script aipm-digest.py --deliver telegram

Config prin env: AIPM_URL (implicit http://127.0.0.1:8090),
AIPM_ENV_FILE (implicit ~/PMORG/.env — de unde se citește AIPM_AUTH_TOKEN).
"""

import json
import os
import sys
import urllib.request

AIPM_URL = os.environ.get("AIPM_URL", "http://127.0.0.1:8090").rstrip("/")
AIPM_ENV_FILE = os.environ.get(
    "AIPM_ENV_FILE", os.path.expanduser("~/PMORG/.env")
)


def token() -> str:
    tok = os.environ.get("AIPM_TOKEN", "")
    if tok:
        return tok
    if os.path.exists(AIPM_ENV_FILE):
        for line in open(AIPM_ENV_FILE):
            if line.startswith("AIPM_AUTH_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def main() -> int:
    req = urllib.request.Request(
        AIPM_URL + "/api/reports/digest",
        method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token()}"},
        data=json.dumps({"mark": True}).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except Exception as e:  # aipm picat: raportează pe canal, nu tăcere
        print(f"⚠ Digestul memoriei nu a putut fi produs: {e}")
        return 1
    if data.get("new_items", 0) > 0:
        print(data["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
