#!/usr/bin/env python3
"""Conducta email → memorie PMORG (tema 08, L2-email) — evaluare.

Părți derivate din conectorul IMAP Onyx (fork bmvv1995/onyx,
backend/onyx/connectors/imap, licență MIT): decodarea headerelor MIME,
tiparul de fetch per mailbox. Adăugate aici (lipseau în Onyx): threading
(References/In-Reply-To), reply-stripping, semnătură, poarta de intimitate,
identitatea structurală din Odoo, fereastra de context pentru fir.

Legile respectate: poarta înaintea conductei; autor nemapat ⇒ carantină
(evidență fără claim); denylist ⇒ refuz consemnat FĂRĂ conținut; items doar
din mesajul curent (contextul doar dezambiguizează).
"""

import email
import email.header
import email.utils
import imaplib
import json
import pathlib
import re
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "runner"))

from aipm.engine import extraction  # noqa: E402
from pmorg_runner.client import OdooApiClient  # noqa: E402
from pmorg_runner.memory_client import MemoryClient  # noqa: E402

IMAP = ("127.0.0.1", 3143)
DENYLIST = ["parola", "salariul", "pin-ul"]
QUOTE_PATTERNS = [
    re.compile(r"^La data de .{0,40}a scris:\s*$"),
    re.compile(r"^On .{0,60}wrote:\s*$"),
]

INVENTORY = [
    {"code": c, "label_ro": l, "odoo_model": m, "active": True}
    for c, l, m in [
        ("PROJECT", "Proiect", "project.project"),
        ("TASK", "Task", "project.task"),
        ("PARTNER", "Partener", "res.partner"),
        ("PRODUCT", "Produs", "product.template"),
        ("COMPANY", "Compania", "res.company"),
    ]
]


def decode_header(msg, name, default=None):
    # derivat din Onyx imap/models.py (MIT)
    value = msg.get(name, default)
    if not value:
        return None
    decoded, enc = email.header.decode_header(value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(enc or "utf-8", errors="replace")
    return decoded


def body_text(msg):
    if msg.is_multipart():
        html = None
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                return part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/html":
                html = part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace")
        if html:
            return re.sub(r"<[^>]+>", " ", html)
        return ""
    payload = msg.get_payload(decode=True)
    text = payload.decode(msg.get_content_charset() or "utf-8",
                          errors="replace")
    if msg.get_content_type() == "text/html":
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def strip_reply_and_signature(text):
    lines, kept = text.splitlines(), []
    for line in lines:
        if line.strip() == "--":
            break  # semnătura
        if any(p.match(line.strip()) for p in QUOTE_PATTERNS):
            break  # antetul citatului: tot ce urmează e istoric
        if line.startswith(">"):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


class Bridge:
    def __init__(self):
        self.odoo = OdooApiClient("http://127.0.0.1:18070", "pmorg_min_c2",
                                  "admin", "admin", actor_id="email-bridge")
        self.mem = MemoryClient("http://127.0.0.1:18091")
        self.threads = {}   # root Message-ID -> [(author, text)]
        self.report = []

    def identity_for(self, addr):
        ids = self.odoo.execute(
            "pmorg.identity", "search_read",
            [["partner_id.email", "=", addr]], ["id", "name"], limit=1)
        return ids[0] if ids else None

    def process(self, raw):
        msg = email.message_from_bytes(raw)
        mid = decode_header(msg, "Message-ID")
        sender_name, sender_addr = email.utils.parseaddr(
            decode_header(msg, "From") or "")
        date = email.utils.parsedate_to_datetime(msg.get("Date"))
        refs = (msg.get("References") or msg.get("In-Reply-To") or "").split()
        root = refs[0] if refs else mid
        entry = {"mid": mid, "from": sender_addr}

        text = strip_reply_and_signature(body_text(msg))

        # 1. poarta de intimitate — ÎNAINTE de orice procesare/stocare
        if any(term in text.lower() for term in DENYLIST):
            entry["outcome"] = "privacy_blocked"
            self.report.append(entry)  # refuz consemnat, FĂRĂ conținut
            return

        # 2. identitatea structurală
        identity = self.identity_for(sender_addr)
        if not identity:
            entry["outcome"] = "quarantined_unknown_sender"
            self.report.append(entry)
            return

        # 3. fereastra de context (firul)
        context = self.threads.get(root, [])
        source = text
        if context:
            ctx = "\n".join(f"{a}: {t}" for a, t in context[-3:])
            source = (f"[CONTEXT FIR — NU consemna nimic din context; "
                      f"folosește-l doar ca să interpretezi mesajul curent]\n"
                      f"{ctx}\n"
                      f"[MESAJ CURENT, autor {sender_name}]\n{text}")
        self.threads.setdefault(root, []).append((sender_name, text))

        # 4. grefierul
        items = extraction.extract(source, sender_name, None, date, INVENTORY)

        # 5. memoria: evidență + claims ancorate la identitatea autorului
        ev = self.mem.ok("memory_capture_evidence", external_id=mid,
                         source="channel:email", author_ref=sender_addr,
                         content=text,
                         correlation_id=root,
                         received_at=str(date))
        for item in items:
            self.mem.ok("memory_propose_claim",
                        statement=f"{item.kind}: {item.title}"
                                  + (f" (termen {item.due_at})"
                                     if item.due_at else ""),
                        author_ref=sender_addr,
                        evidence_ids=[ev["evidence_id"]],
                        anchors=[{"anchor_type": "IDENTITY",
                                  "model": "pmorg.identity",
                                  "res_id": identity["id"],
                                  "role": "subject"}])
        entry["outcome"] = "processed"
        entry["items"] = [
            {"kind": i.kind, "title": i.title, "due_at": str(i.due_at or "")}
            for i in items]
        self.report.append(entry)

    def run(self):
        client = imaplib.IMAP4(*IMAP)  # test server: fără SSL (Onyx: doar SSL)
        client.login("pm@atelier-min.example", "x")
        client.select("INBOX")
        _, data = client.search(None, "ALL")
        for num in data[0].split():
            _, msg_data = client.fetch(num, "(RFC822)")
            self.process(msg_data[0][1])
        return self.report


def score(report, cases):
    by_mid = {e["mid"]: e for e in report}
    passed = 0
    for case in cases:
        exp, entry = case["expected"], by_mid.get(case["mid"])
        problems = []
        if exp.get("privacy_blocked"):
            if not entry or entry["outcome"] != "privacy_blocked":
                problems.append("nu a fost blocat de poartă")
        elif exp.get("quarantine"):
            if not entry or entry["outcome"] != "quarantined_unknown_sender":
                problems.append("nu a fost carantinat")
        else:
            if not entry or entry["outcome"] != "processed":
                problems.append(f"outcome={entry and entry['outcome']}")
            else:
                got = Counter(i["kind"] for i in entry["items"])
                for kind in exp.get("require", []):
                    if not got.get(kind):
                        problems.append(f"lipsă {kind}")
                for kind in exp.get("forbid", []):
                    if got.get(kind):
                        problems.append(f"inventat {kind}")
                if "max_commitments" in exp and \
                        got.get("commitment", 0) > exp["max_commitments"]:
                    problems.append("citatul re-extras (dublă contorizare)")
                if "due" in exp:
                    kind, want = exp["due"]
                    dues = [i["due_at"] for i in entry["items"]
                            if i["kind"] == kind]
                    if want not in dues:
                        problems.append(f"termen: {dues} ≠ {want}")
        okk = not problems
        passed += okk
        print(f"[{'PASS' if okk else 'FAIL'}] {case['mid']}: "
              f"{'; '.join(problems) or 'ok'}")
    print(f"\n===== EMAIL BRIDGE: {passed}/{len(cases)} =====")
    return passed == len(cases)


if __name__ == "__main__":
    cases = json.load(open(sys.argv[1]))
    bridge = Bridge()
    report = bridge.run()
    sys.exit(0 if score(report, cases) else 1)
