#!/usr/bin/env python3
"""Adaptorul de memorie sub contractul pmorg-memory/1.0 (S3 — convergența).

Expune stratul de claims (migrația 0008) peste nucleul aipm: același pool
psycopg, aceleași migrații, același inventar guvernat de ancore. Wire-contract
identic cu serviciul v2 (JSON-RPC, metode memory_*, erori MEM_*): runnerul și
suita de acceptanță rulează neschimbate.

Fail-closed la boot (02-MVP §4.3): fără default-uri de producție; lipsa
oricărei variabile oprește procesul înainte de rețea. Ingestul aipm (poller
chatter) NU pornește aici — adaptorul e strict suprafața de contract.

Autoritatea vocabularului: profilul cere un subset de tipuri; fiecare tip
trebuie să existe ACTIV în tabela anchor_type (inventarul închis, SPEC §1.1).
Un tip absent din inventar ⇒ refuz la boot, nu fallback.
"""

import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONTRACT = "pmorg-memory/1.0"

PROFILE_TYPES = {
    "org-min": ["COMPANY", "PROJECT", "TASK", "INITIATIVE", "IDENTITY"],
    "org-services": ["COMPANY", "PROJECT", "TASK", "INITIATIVE", "IDENTITY",
                     "EMPLOYEE", "DEPARTMENT", "LEAVE_REQUEST"],
    "org-distribution": ["COMPANY", "PROJECT", "TASK", "INITIATIVE", "IDENTITY",
                         "EMPLOYEE", "DEPARTMENT",
                         "INVENTORY_TRANSFER", "INVENTORY_MOVE"],
}
# Tipuri v2 care nu au (încă) rând în inventarul aipm v1 — packs de domeniu
# viitoare (hr/stock nu sunt în lumea aipm v1). Se acceptă din PROFILE_TYPES
# doar dacă există în anchor_type; excepțiile declarate aici sunt tolerate cu
# modelul din harta v2, până la migrația care le adaugă în inventar.
V2_ONLY_TYPES = {
    "LEAVE_REQUEST": "hr.leave",
    "EMPLOYEE": "hr.employee",
    "DEPARTMENT": "hr.department",
    "INVENTORY_TRANSFER": "stock.picking",
    "INVENTORY_MOVE": "stock.move",
}


class MemError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class Config:
    REQUIRED = (
        "PMORG_PROFILE_ID",
        "PMORG_RUN_ID",
        "PMORG_INSTANCE_UUID",
        "PMORG_NAMESPACE",
        "PMORG_PG_HOST",
        "PMORG_PG_DB",
        "PMORG_PG_USER",
        "PMORG_PG_PASSWORD_FILE",
        "PMORG_AUTHORIZED_VALIDATORS",
    )
    ALLOWED_PG_HOSTS = {"db", "127.0.0.1", "localhost"}

    def __init__(self, env):
        missing = [k for k in self.REQUIRED if not env.get(k)]
        if missing:
            raise SystemExit(f"FAIL-CLOSED: variabile lipsă: {missing}")
        if env["PMORG_PG_HOST"] not in self.ALLOWED_PG_HOSTS:
            raise SystemExit(
                f"FAIL-CLOSED: PG host neautorizat: {env['PMORG_PG_HOST']}"
            )
        if env["PMORG_PROFILE_ID"] not in PROFILE_TYPES:
            raise SystemExit(
                f"FAIL-CLOSED: profil necunoscut: {env['PMORG_PROFILE_ID']}"
            )
        self.profile_id = env["PMORG_PROFILE_ID"]
        self.run_id = env["PMORG_RUN_ID"]
        self.instance_uuid = env["PMORG_INSTANCE_UUID"]
        self.namespace = env["PMORG_NAMESPACE"]
        with open(env["PMORG_PG_PASSWORD_FILE"], encoding="utf-8") as handle:
            password = handle.read().strip()
        self.pg_dsn = (
            f"host={env['PMORG_PG_HOST']} dbname={env['PMORG_PG_DB']} "
            f"user={env['PMORG_PG_USER']} password={password}"
        )
        self.validators = {
            v.strip()
            for v in env["PMORG_AUTHORIZED_VALIDATORS"].split(",")
            if v.strip()
        }
        self.bind_port = int(env.get("PMORG_BIND_PORT", "8091"))


class MemoryAdapter:
    def __init__(self, cfg):
        self.cfg = cfg
        from aipm import config as aipm_config

        aipm_config.PG_DSN = cfg.pg_dsn  # nucleul aipm pe baza sandbox-ului
        from aipm import db as aipm_db
        from aipm.migrations.migrate import run as migrate_run

        migrate_run(cfg.pg_dsn)  # migrațiile aipm 0001..0008, forward-only
        self.db = aipm_db
        self.registry = self._load_registry()

    # ------------------------------------------------------------ registry

    def _load_registry(self):
        """Vocabularul profilului, validat contra inventarului închis aipm."""
        with self.db.transaction() as conn:
            rows = conn.execute(
                "SELECT code, odoo_model FROM anchor_type WHERE active"
            ).fetchall()
        inventory = {r["code"]: r["odoo_model"] for r in rows}
        types = {}
        for code in PROFILE_TYPES[self.cfg.profile_id]:
            if code in inventory:
                types[code] = inventory[code]
            elif code in V2_ONLY_TYPES:
                types[code] = V2_ONLY_TYPES[code]
            else:
                raise SystemExit(
                    f"FAIL-CLOSED: tipul {code} lipsește din inventarul anchor_type."
                )
        return {"registry_version": "1.0", "anchor_types": types}

    def _fingerprint(self):
        return hashlib.sha256(
            json.dumps(self.registry, sort_keys=True).encode()
        ).hexdigest()

    # --------------------------------------------------------------- tools

    def memory_negotiate_registry(self, p, conn):
        if p.get("profile_id") != self.cfg.profile_id:
            raise MemError(
                "MEM_REGISTRY_MISMATCH",
                f"Serviciul rulează profilul {self.cfg.profile_id}.",
            )
        fp = self._fingerprint()
        if p.get("expected_fingerprint") and p["expected_fingerprint"] != fp:
            raise MemError("MEM_REGISTRY_MISMATCH", "Fingerprint diferit.")
        return dict(
            self.registry,
            fingerprint=fp,
            namespace=self.cfg.namespace,
            run_id=self.cfg.run_id,
        )

    def memory_capture_evidence(self, p, conn):
        for key in ("external_id", "source", "author_ref", "content"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        digest = hashlib.sha256(p["content"].encode()).hexdigest()
        if p.get("content_hash") and p["content_hash"] != digest:
            raise MemError("MEM_HASH_MISMATCH", "Hash-ul nu corespunde conținutului.")
        row = conn.execute(
            "SELECT id FROM mem_evidence WHERE namespace=%s AND external_id=%s",
            (self.cfg.namespace, p["external_id"]),
        ).fetchone()
        if row:
            return {"evidence_id": row["id"], "content_hash": digest,
                    "replayed": True}
        row = conn.execute(
            """INSERT INTO mem_evidence
               (namespace, external_id, source, author_ref, content,
                content_hash, correlation_id, received_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (self.cfg.namespace, p["external_id"], p["source"], p["author_ref"],
             p["content"], digest, p.get("correlation_id"), p.get("received_at")),
        ).fetchone()
        return {"evidence_id": row["id"], "content_hash": digest,
                "replayed": False}

    def _check_anchors(self, anchors):
        reg = self.registry["anchor_types"]
        for anchor in anchors:
            atype = anchor.get("anchor_type")
            if atype not in reg:
                raise MemError(
                    "MEM_ANCHOR_TYPE_UNKNOWN",
                    f"Tip de ancoră în afara registry-ului negociat: {atype}.",
                )
            if reg[atype] != anchor.get("model"):
                raise MemError(
                    "MEM_ANCHOR_TYPE_UNKNOWN",
                    f"Modelul {anchor.get('model')} nu corespunde tipului {atype}.",
                )
            if not anchor.get("res_id"):
                raise MemError("MEM_SCHEMA", "Ancoră fără res_id.")

    def memory_propose_claim(self, p, conn):
        for key in ("statement", "author_ref", "evidence_ids"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        anchors = p.get("anchors") or []
        if not anchors:
            raise MemError("MEM_SCHEMA", "Un claim cere cel puțin o ancoră.")
        self._check_anchors(anchors)
        found = {
            r["id"]
            for r in conn.execute(
                "SELECT id FROM mem_evidence WHERE namespace=%s AND id = ANY(%s)",
                (self.cfg.namespace, p["evidence_ids"]),
            ).fetchall()
        }
        missing = set(p["evidence_ids"]) - found
        if missing:
            raise MemError("MEM_UNKNOWN", f"Evidențe inexistente: {sorted(missing)}.")
        row = conn.execute(
            """INSERT INTO mem_claim
               (namespace, statement, author_ref, evidence_ids, anchors)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (self.cfg.namespace, p["statement"], p["author_ref"],
             p["evidence_ids"], json.dumps(anchors)),
        ).fetchone()
        return {"claim_id": row["id"], "status": "candidate"}

    def memory_validate_claim(self, p, conn):
        for key in ("claim_id", "validator_ref", "supporting_evidence_id"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        claim = conn.execute(
            "SELECT * FROM mem_claim WHERE namespace=%s AND id=%s",
            (self.cfg.namespace, p["claim_id"]),
        ).fetchone()
        if not claim:
            raise MemError("MEM_UNKNOWN", f"Claim inexistent: {p['claim_id']}.")
        if claim["status"] != "candidate":
            raise MemError("MEM_STATE", f"Claim în starea {claim['status']}.")
        if p["validator_ref"] not in self.cfg.validators:
            raise MemError(
                "MEM_NOT_AUTHORIZED",
                "Validatorul nu este autorizat de politica profilului.",
            )
        if p["validator_ref"] == claim["author_ref"]:
            raise MemError(
                "MEM_SELF_VALIDATION",
                "Autorul nu își poate valida propria afirmație.",
            )
        evidence = conn.execute(
            "SELECT * FROM mem_evidence WHERE namespace=%s AND id=%s",
            (self.cfg.namespace, p["supporting_evidence_id"]),
        ).fetchone()
        if not evidence:
            raise MemError(
                "MEM_UNKNOWN",
                f"Dovadă inexistentă: {p['supporting_evidence_id']}.",
            )
        if evidence["author_ref"] == claim["author_ref"]:
            raise MemError(
                "MEM_SELF_VALIDATION",
                "Dovada de validare trebuie să aibă autor independent.",
            )
        expected = p.get("expected_content_hash")
        if expected and expected != evidence["content_hash"]:
            raise MemError("MEM_HASH_MISMATCH", "Hash-ul dovezii nu corespunde.")
        conn.execute(
            """UPDATE mem_claim SET status='validated', validated_by=%s,
               validated_at=now(), validation_evidence_id=%s WHERE id=%s""",
            (p["validator_ref"], evidence["id"], claim["id"]),
        )
        return {"claim_id": claim["id"], "status": "validated"}

    def memory_supersede(self, p, conn):
        for key in ("old_claim_id", "new_claim_id", "reason"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        rows = {
            r["id"]: r
            for r in conn.execute(
                "SELECT id, status FROM mem_claim "
                "WHERE namespace=%s AND id IN (%s, %s)",
                (self.cfg.namespace, p["old_claim_id"], p["new_claim_id"]),
            ).fetchall()
        }
        if len(rows) != 2:
            raise MemError("MEM_UNKNOWN", "Claim-uri inexistente.")
        if rows[p["old_claim_id"]]["status"] == "superseded":
            raise MemError("MEM_STATE", "Claim-ul vechi e deja înlocuit.")
        conn.execute(
            """UPDATE mem_claim SET status='superseded', superseded_by=%s,
               supersede_reason=%s WHERE id=%s""",
            (p["new_claim_id"], p["reason"], p["old_claim_id"]),
        )
        return {"old_claim_id": p["old_claim_id"], "status": "superseded"}

    def memory_record_outcome(self, p, conn):
        for key in ("task_ref", "summary", "evidence_ids"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        row = conn.execute(
            """INSERT INTO mem_outcome (namespace, task_ref, claim_id, summary,
               evidence_ids) VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (self.cfg.namespace, p["task_ref"], p.get("claim_id"),
             p["summary"], p["evidence_ids"]),
        ).fetchone()
        return {"outcome_id": row["id"]}

    def _anchor_filter(self, anchor):
        return json.dumps([{
            "anchor_type": anchor["anchor_type"],
            "model": anchor["model"],
            "res_id": anchor["res_id"],
        }])

    def memory_recall(self, p, conn):
        anchor = p.get("anchor")
        if not anchor:
            raise MemError("MEM_SCHEMA", "Recall cere o ancoră.")
        self._check_anchors([anchor])
        claims = [
            dict(r)
            for r in conn.execute(
                """SELECT id, statement, status, author_ref, validated_by,
                          superseded_by, evidence_ids FROM mem_claim
                   WHERE namespace=%s AND anchors @> %s::jsonb ORDER BY id""",
                (self.cfg.namespace, self._anchor_filter(anchor)),
            ).fetchall()
        ]
        for claim in claims:
            claim["epistemic_label"] = (
                "validated" if claim["status"] == "validated" else "hypothesis"
            )
        return {"claims": claims}

    def memory_get_timeline(self, p, conn):
        anchor = p.get("anchor")
        if not anchor:
            raise MemError("MEM_SCHEMA", "Timeline cere o ancoră.")
        self._check_anchors([anchor])
        rows = conn.execute(
            """SELECT 'claim' AS kind, id, created_at, status, statement AS text
               FROM mem_claim WHERE namespace=%s AND anchors @> %s::jsonb
               UNION ALL
               SELECT 'outcome', o.id, o.created_at, 'recorded', o.summary
               FROM mem_outcome o
               JOIN mem_claim c ON c.id = o.claim_id
               WHERE o.namespace=%s AND c.anchors @> %s::jsonb
               ORDER BY created_at, id""",
            (self.cfg.namespace, self._anchor_filter(anchor),
             self.cfg.namespace, self._anchor_filter(anchor)),
        ).fetchall()
        return {"events": [dict(r, created_at=str(r["created_at"]))
                           for r in rows]}

    # ------------------------------------------------------------ dispatch

    def dispatch(self, method, params):
        if params.get("contract") != CONTRACT:
            raise MemError(
                "MEM_CONTRACT", f"Contract necunoscut: {params.get('contract')}."
            )
        handler = getattr(self, method, None)
        if not handler or not method.startswith("memory_"):
            raise MemError("MEM_SCHEMA", f"Metodă necunoscută: {method}.")
        with self.db.transaction() as conn:
            return handler(params, conn)


def make_handler(adapter):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            try:
                request = json.loads(self.rfile.read(length))
                result = adapter.dispatch(
                    request.get("method", ""), request.get("params") or {}
                )
                body = {"jsonrpc": "2.0", "id": request.get("id"),
                        "result": result}
            except MemError as exc:
                body = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": exc.code, "message": exc.message}}
            except Exception as exc:
                body = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": "MEM_INTERNAL", "message": str(exc)}}
            payload = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def main():
    cfg = Config(os.environ)
    adapter = MemoryAdapter(cfg)
    server = ThreadingHTTPServer(("0.0.0.0", cfg.bind_port),
                                 make_handler(adapter))
    print(
        f"pmorg-memory {CONTRACT} (adaptor aipm) profil={cfg.profile_id} "
        f"namespace={cfg.namespace} port={cfg.bind_port} "
        f"tipuri={sorted(adapter.registry['anchor_types'])}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
