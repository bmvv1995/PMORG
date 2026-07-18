#!/usr/bin/env python3
"""Serviciul de memorie PMORG — contract pmorg-memory/1.0 (Gate B).

Extern față de Odoo (ADR-004), determinist (fără LLM), fail-closed la boot
(02-MVP §4.3: fără defaulturi de producție; lipsa run_id/profile_id/
instance UUID/namespace/DSN allow-listed oprește serviciul înainte de rețea).

Persistență reală PostgreSQL. Validarea claims e mecanică: autorul nu își
poate valida propria afirmație, dovada trebuie să existe și hash-ul să
corespundă, validatorul trebuie autorizat de politica profilului.

Notă de reconciliere: transportul este JSON-RPC 2.0 peste HTTP; legarea la
protocolul MCP standard (stdio) e o anvelopă subțire peste aceleași tool-uri
și se adaugă la integrarea agentică (Gate E). Suprafața și semantica sunt
cele din 02-MVP §4.3.
"""

import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2
import psycopg2.extras

CONTRACT = "pmorg-memory/1.0"

CORE_TYPES = {
    "COMPANY": "res.company",
    "PROJECT": "project.project",
    "TASK": "project.task",
    "INITIATIVE": "pmorg.initiative",
    "IDENTITY": "pmorg.identity",
}
HR_TYPES = {"EMPLOYEE": "hr.employee", "DEPARTMENT": "hr.department"}
INVENTORY_TYPES = {
    "INVENTORY_TRANSFER": "stock.picking",
    "INVENTORY_MOVE": "stock.move",
}

REGISTRIES = {
    "org-min": {
        "registry_version": "1.0",
        "anchor_types": dict(CORE_TYPES),
    },
    "org-services": {
        "registry_version": "1.0",
        "anchor_types": dict(CORE_TYPES, **HR_TYPES),
    },
    "org-distribution": {
        "registry_version": "1.0",
        "anchor_types": dict(CORE_TYPES, **HR_TYPES, **INVENTORY_TYPES),
    },
}

DDL = """
CREATE TABLE IF NOT EXISTS evidence (
    id            serial PRIMARY KEY,
    namespace     text NOT NULL,
    external_id   text NOT NULL,
    source        text NOT NULL,
    author_ref    text NOT NULL,
    content       text NOT NULL,
    content_hash  text NOT NULL,
    correlation_id text,
    received_at   text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (namespace, external_id)
);
CREATE TABLE IF NOT EXISTS claim (
    id            serial PRIMARY KEY,
    namespace     text NOT NULL,
    statement     text NOT NULL,
    status        text NOT NULL DEFAULT 'candidate'
                  CHECK (status IN ('candidate','validated','refuted','superseded')),
    author_ref    text NOT NULL,
    evidence_ids  integer[] NOT NULL DEFAULT '{}',
    anchors       jsonb NOT NULL DEFAULT '[]',
    validated_by  text,
    validated_at  timestamptz,
    validation_evidence_id integer,
    superseded_by integer,
    supersede_reason text,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS outcome (
    id            serial PRIMARY KEY,
    namespace     text NOT NULL,
    task_ref      text NOT NULL,
    claim_id      integer,
    summary       text NOT NULL,
    evidence_ids  integer[] NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now()
);
"""


class MemError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class Config:
    """Boot fail-closed: totul explicit, nimic moștenit din producție."""

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
        if env["PMORG_PROFILE_ID"] not in REGISTRIES:
            raise SystemExit(
                f"FAIL-CLOSED: profil necunoscut: {env['PMORG_PROFILE_ID']}"
            )
        self.profile_id = env["PMORG_PROFILE_ID"]
        self.run_id = env["PMORG_RUN_ID"]
        self.instance_uuid = env["PMORG_INSTANCE_UUID"]
        self.namespace = env["PMORG_NAMESPACE"]
        with open(env["PMORG_PG_PASSWORD_FILE"], encoding="utf-8") as handle:
            password = handle.read().strip()
        self.dsn = (
            f"host={env['PMORG_PG_HOST']} dbname={env['PMORG_PG_DB']} "
            f"user={env['PMORG_PG_USER']} password={password}"
        )
        self.validators = {
            v.strip() for v in env["PMORG_AUTHORIZED_VALIDATORS"].split(",") if v.strip()
        }
        self.bind_port = int(env.get("PMORG_BIND_PORT", "8091"))


def registry_fingerprint(profile_id):
    canonical = json.dumps(REGISTRIES[profile_id], sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


class MemoryService:
    def __init__(self, config):
        self.cfg = config

    def _conn(self):
        return psycopg2.connect(
            self.cfg.dsn, cursor_factory=psycopg2.extras.RealDictCursor
        )

    def init_schema(self):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(DDL)

    # ------------------------------------------------------------- tools

    def memory_negotiate_registry(self, p, cur):
        if p.get("profile_id") != self.cfg.profile_id:
            raise MemError(
                "MEM_REGISTRY_MISMATCH",
                f"Serviciul rulează profilul {self.cfg.profile_id}.",
            )
        fp = registry_fingerprint(self.cfg.profile_id)
        expected = p.get("expected_fingerprint")
        if expected and expected != fp:
            raise MemError("MEM_REGISTRY_MISMATCH", "Fingerprint diferit.")
        reg = REGISTRIES[self.cfg.profile_id]
        return {
            "registry_version": reg["registry_version"],
            "anchor_types": reg["anchor_types"],
            "fingerprint": fp,
            "namespace": self.cfg.namespace,
            "run_id": self.cfg.run_id,
        }

    def memory_capture_evidence(self, p, cur):
        for key in ("external_id", "source", "author_ref", "content"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        digest = hashlib.sha256(p["content"].encode()).hexdigest()
        if p.get("content_hash") and p["content_hash"] != digest:
            raise MemError("MEM_HASH_MISMATCH", "Hash-ul nu corespunde conținutului.")
        cur.execute(
            "SELECT id FROM evidence WHERE namespace=%s AND external_id=%s",
            (self.cfg.namespace, p["external_id"]),
        )
        row = cur.fetchone()
        if row:
            return {"evidence_id": row["id"], "content_hash": digest, "replayed": True}
        cur.execute(
            """INSERT INTO evidence
               (namespace, external_id, source, author_ref, content,
                content_hash, correlation_id, received_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (
                self.cfg.namespace,
                p["external_id"],
                p["source"],
                p["author_ref"],
                p["content"],
                digest,
                p.get("correlation_id"),
                p.get("received_at"),
            ),
        )
        return {
            "evidence_id": cur.fetchone()["id"],
            "content_hash": digest,
            "replayed": False,
        }

    def _check_anchors(self, anchors):
        reg = REGISTRIES[self.cfg.profile_id]["anchor_types"]
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

    def memory_propose_claim(self, p, cur):
        for key in ("statement", "author_ref", "evidence_ids"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        anchors = p.get("anchors") or []
        if not anchors:
            raise MemError("MEM_SCHEMA", "Un claim cere cel puțin o ancoră.")
        self._check_anchors(anchors)
        cur.execute(
            "SELECT id FROM evidence WHERE namespace=%s AND id = ANY(%s)",
            (self.cfg.namespace, p["evidence_ids"]),
        )
        found = {r["id"] for r in cur.fetchall()}
        missing = set(p["evidence_ids"]) - found
        if missing:
            raise MemError("MEM_UNKNOWN", f"Evidențe inexistente: {sorted(missing)}.")
        cur.execute(
            """INSERT INTO claim
               (namespace, statement, author_ref, evidence_ids, anchors)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (
                self.cfg.namespace,
                p["statement"],
                p["author_ref"],
                p["evidence_ids"],
                json.dumps(anchors),
            ),
        )
        return {"claim_id": cur.fetchone()["id"], "status": "candidate"}

    def memory_validate_claim(self, p, cur):
        for key in ("claim_id", "validator_ref", "supporting_evidence_id"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        cur.execute(
            "SELECT * FROM claim WHERE namespace=%s AND id=%s",
            (self.cfg.namespace, p["claim_id"]),
        )
        claim = cur.fetchone()
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
        cur.execute(
            "SELECT * FROM evidence WHERE namespace=%s AND id=%s",
            (self.cfg.namespace, p["supporting_evidence_id"]),
        )
        evidence = cur.fetchone()
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
        cur.execute(
            """UPDATE claim SET status='validated', validated_by=%s,
               validated_at=now(), validation_evidence_id=%s WHERE id=%s""",
            (p["validator_ref"], evidence["id"], claim["id"]),
        )
        return {"claim_id": claim["id"], "status": "validated"}

    def memory_supersede(self, p, cur):
        for key in ("old_claim_id", "new_claim_id", "reason"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        cur.execute(
            "SELECT id, status FROM claim WHERE namespace=%s AND id IN (%s, %s)",
            (self.cfg.namespace, p["old_claim_id"], p["new_claim_id"]),
        )
        rows = {r["id"]: r for r in cur.fetchall()}
        if len(rows) != 2:
            raise MemError("MEM_UNKNOWN", "Claim-uri inexistente.")
        if rows[p["old_claim_id"]]["status"] == "superseded":
            raise MemError("MEM_STATE", "Claim-ul vechi e deja înlocuit.")
        cur.execute(
            """UPDATE claim SET status='superseded', superseded_by=%s,
               supersede_reason=%s WHERE id=%s""",
            (p["new_claim_id"], p["reason"], p["old_claim_id"]),
        )
        return {"old_claim_id": p["old_claim_id"], "status": "superseded"}

    def memory_record_outcome(self, p, cur):
        for key in ("task_ref", "summary", "evidence_ids"):
            if not p.get(key):
                raise MemError("MEM_SCHEMA", f"Câmp lipsă: {key}.")
        cur.execute(
            """INSERT INTO outcome (namespace, task_ref, claim_id, summary,
               evidence_ids) VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (
                self.cfg.namespace,
                p["task_ref"],
                p.get("claim_id"),
                p["summary"],
                p["evidence_ids"],
            ),
        )
        return {"outcome_id": cur.fetchone()["id"]}

    def _anchor_filter(self, anchor):
        return json.dumps(
            [{
                "anchor_type": anchor["anchor_type"],
                "model": anchor["model"],
                "res_id": anchor["res_id"],
            }]
        )

    def memory_recall(self, p, cur):
        anchor = p.get("anchor")
        if not anchor:
            raise MemError("MEM_SCHEMA", "Recall cere o ancoră.")
        self._check_anchors([anchor])
        cur.execute(
            """SELECT id, statement, status, author_ref, validated_by,
                      superseded_by, evidence_ids FROM claim
               WHERE namespace=%s AND anchors @> %s::jsonb ORDER BY id""",
            (self.cfg.namespace, self._anchor_filter(anchor)),
        )
        claims = [dict(r) for r in cur.fetchall()]
        for claim in claims:
            claim["epistemic_label"] = (
                "validated" if claim["status"] == "validated" else "hypothesis"
            )
        return {"claims": claims}

    def memory_get_timeline(self, p, cur):
        anchor = p.get("anchor")
        if not anchor:
            raise MemError("MEM_SCHEMA", "Timeline cere o ancoră.")
        self._check_anchors([anchor])
        cur.execute(
            """SELECT 'claim' AS kind, id, created_at, status, statement AS text
               FROM claim WHERE namespace=%s AND anchors @> %s::jsonb
               UNION ALL
               SELECT 'outcome', o.id, o.created_at, 'recorded', o.summary
               FROM outcome o
               JOIN claim c ON c.id = o.claim_id
               WHERE o.namespace=%s AND c.anchors @> %s::jsonb
               ORDER BY created_at, id""",
            (
                self.cfg.namespace,
                self._anchor_filter(anchor),
                self.cfg.namespace,
                self._anchor_filter(anchor),
            ),
        )
        return {"events": [dict(r, created_at=str(r["created_at"]))
                           for r in cur.fetchall()]}

    def dispatch(self, method, params):
        if params.get("contract") != CONTRACT:
            raise MemError(
                "MEM_CONTRACT", f"Contract necunoscut: {params.get('contract')}."
            )
        handler = getattr(self, method, None)
        if not handler or not method.startswith("memory_"):
            raise MemError("MEM_SCHEMA", f"Metodă necunoscută: {method}.")
        with self._conn() as conn, conn.cursor() as cur:
            return handler(params, cur)


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            try:
                request = json.loads(self.rfile.read(length))
                result = service.dispatch(
                    request.get("method", ""), request.get("params") or {}
                )
                body = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
            except MemError as exc:
                body = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": exc.code, "message": exc.message},
                }
            except Exception as exc:  # defect intern — vizibil, nu tăcut
                body = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": "MEM_INTERNAL", "message": str(exc)},
                }
            payload = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def main():
    config = Config(os.environ)
    service = MemoryService(config)
    service.init_schema()
    server = ThreadingHTTPServer(("0.0.0.0", config.bind_port),
                                 make_handler(service))
    print(
        f"pmorg-memory {CONTRACT} profil={config.profile_id} "
        f"namespace={config.namespace} port={config.bind_port}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
