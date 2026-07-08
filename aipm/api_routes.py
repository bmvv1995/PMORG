"""Endpoint-urile API de produs (plan §8).

Handler-e sincrone (def) — FastAPI le rulează în threadpool; stack-ul e sincron (plan §7).
"""

import logging
import threading
import uuid as uuid_mod

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import config, db
from .adapter.contract import AdapterError
from .engine import recall, receipts
from .ingest import ingest_lock

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    message_uuid: str | None = None


class ReviewAction(BaseModel):
    action: str  # confirm | reassign | remove
    res_id: int | None = None


class ExternalStatus(BaseModel):
    status: str  # dismissed | created


class ReplayRequest(BaseModel):
    source_ref: str


class DigestRequest(BaseModel):
    mark: bool = True


class GatewayIngest(BaseModel):
    author_key: str
    text: str
    chat_id: str = ""
    session_id: str = ""


def _memory_row(conn, row) -> dict:
    item = dict(row) | {"id": str(row["id"])}
    for key in ("created_at", "due_at"):
        if item.get(key) is not None:
            item[key] = str(item[key])
    anchors = conn.execute(
        """SELECT ma.id, ma.anchor_code, ma.odoo_res_id, ma.role, ma.confidence,
                  ma.resolved_by, ma.needs_review, ma.mention_text,
                  at.label_ro, at.odoo_model, at.url_template
           FROM memory_anchor ma JOIN anchor_type at ON at.code = ma.anchor_code
           WHERE ma.memory_id = %s ORDER BY ma.role""",
        (row["id"],),
    ).fetchall()
    item["anchors"] = [
        dict(a)
        | {
            "confidence": float(a["confidence"]),
            "url": a["url_template"].format(
                base_url=config.ODOO_BASE_URL,
                odoo_model=a["odoo_model"],
                odoo_res_id=a["odoo_res_id"],
            ),
        }
        for a in anchors
    ]
    for a in item["anchors"]:
        del a["url_template"]
    receipt = conn.execute(
        "SELECT anchor_code, odoo_res_id, mail_message_id, posted_at FROM memory_receipt WHERE memory_id=%s",
        (row["id"],),
    ).fetchone()
    item["receipt"] = dict(receipt) | {"posted_at": str(receipt["posted_at"])} if receipt else None
    return item


def register(app: FastAPI) -> None:
    @app.post("/api/chat")
    def chat(req: ChatRequest):
        message_uuid = req.message_uuid
        if message_uuid:
            try:
                uuid_mod.UUID(message_uuid)
            except ValueError:
                raise HTTPException(422, "message_uuid trebuie să fie UUID valid")
        else:
            # client non-UI: fără garanție de idempotență (plan A.§3, documentat)
            message_uuid = str(uuid_mod.uuid4())

        result = recall.answer(req.message, req.session_id)

        # ingestul mesajului utilizatorului — asincron, DUPĂ răspuns (plan A.§3)
        from .ingest.chat_source import ingest_chat_message

        threading.Thread(
            target=ingest_chat_message,
            args=(result["session_id"], message_uuid, req.message),
            daemon=True,
        ).start()
        return result

    @app.post("/api/recall")
    def recall_only(req: ChatRequest):
        """Citire PURĂ (PLAN-INTEGRARE etapa 7) — calea uneltelor PM-ului prin MCP.

        Spre deosebire de /api/chat, întrebarea NU se ingestează: consumatorul e un
        agent, nu un om — textul lui nu devine fapt (P1), deci nu se scrie nimic."""
        return recall.answer(req.message, req.session_id)

    @app.get("/api/memory")
    def memory_list(
        kind: str | None = None,
        anchor_code: str | None = None,
        res_id: int | None = None,
        q: str | None = None,
        since: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
    ):
        clauses, params = ["mi.status != 'retracted'"], []
        if kind:
            clauses.append("mi.kind = %s")
            params.append(kind)
        if anchor_code and res_id is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM memory_anchor ma WHERE ma.memory_id = mi.id"
                " AND ma.anchor_code = %s AND ma.odoo_res_id = %s)"
            )
            params.extend([anchor_code, res_id])
        if q:
            clauses.append("(mi.title ILIKE %s OR mi.body ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
        if since:
            clauses.append("mi.created_at > %s")
            params.append(since)
        if session_id:
            clauses.append("mi.source_ref LIKE %s")
            params.append(f"chat:{session_id}:%")
        with db.transaction() as conn:
            rows = conn.execute(
                f"""SELECT id, kind, title, body, quote, due_at, status, trust,
                           source_type, source_ref, extract_confidence, created_at
                    FROM memory_item mi WHERE {' AND '.join(clauses)}
                    ORDER BY created_at DESC LIMIT %s""",
                params + [min(limit, 200)],
            ).fetchall()
            return {"items": [_memory_row(conn, r) for r in rows]}

    @app.get("/api/memory/{memory_id}")
    def memory_get(memory_id: str):
        with db.transaction() as conn:
            row = conn.execute(
                """SELECT id, kind, title, body, quote, due_at, status, trust,
                          source_type, source_ref, extract_confidence, created_at
                   FROM memory_item WHERE id=%s""",
                (memory_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "memory_item inexistent")
            return _memory_row(conn, row)

    @app.post("/api/memory/{memory_id}/resolve")
    def memory_resolve(memory_id: str):
        """Felia A (etapa 8, D3): OMUL marchează angajamentul încheiat/înlocuit.
        Audit P5: resolved_by + resolved_at. Itemii 'resolved' ies din rapoarte
        și din recall prin filtrele status='active' existente."""
        with db.transaction() as conn:
            updated = conn.execute(
                """UPDATE memory_item
                   SET status='resolved', resolved_by='human', resolved_at=now()
                   WHERE id=%s AND status='active' RETURNING id""",
                (memory_id,),
            ).fetchone()
            if updated is None:
                existing = conn.execute(
                    "SELECT status FROM memory_item WHERE id=%s", (memory_id,)
                ).fetchone()
                if existing is None:
                    raise HTTPException(404, "memory_item inexistent")
                raise HTTPException(
                    409, f"item cu status '{existing['status']}' — doar 'active' se poate rezolva"
                )
        return {"status": "resolved"}

    @app.post("/api/memory/{memory_id}/retract")
    def memory_retract(memory_id: str):
        with db.transaction() as conn:
            updated = conn.execute(
                "UPDATE memory_item SET status='retracted' WHERE id=%s RETURNING id",
                (memory_id,),
            ).fetchone()
        if updated is None:
            raise HTTPException(404, "memory_item inexistent")
        return {"status": "retracted"}

    @app.post("/api/memory/{memory_id}/post-receipt")
    def memory_post_receipt(memory_id: str):
        try:
            return receipts.post_receipt(memory_id)
        except receipts.NoSubjectAnchor:
            raise HTTPException(
                409, "item fără ancoră subject rezolvată — confirmă/realocă subiectul întâi"
            )
        except receipts.NoChatterTarget:
            raise HTTPException(409, "nicio ancoră cu chatter — chitanța nu are țintă")
        except AdapterError as e:
            raise HTTPException(502, f"Odoo indisponibil: {e}")
        except ValueError:
            raise HTTPException(404, "memory_item inexistent")

    @app.get("/api/review/queue")
    def review_queue():
        with db.transaction() as conn:
            anchor_rows = conn.execute(
                """SELECT mi.id FROM memory_item mi
                   WHERE mi.status='active' AND EXISTS (
                     SELECT 1 FROM memory_anchor ma
                     WHERE ma.memory_id = mi.id AND ma.needs_review)
                   ORDER BY mi.created_at DESC LIMIT 100"""
            ).fetchall()
            untrusted_rows = conn.execute(
                """SELECT mi.id FROM memory_item mi
                   WHERE mi.status='active' AND mi.trust=0
                   ORDER BY mi.created_at DESC LIMIT 100"""
            ).fetchall()

            def _load(ids):
                out = []
                for r in ids:
                    row = conn.execute(
                        """SELECT id, kind, title, body, quote, due_at, status, trust,
                                  source_type, source_ref, extract_confidence, created_at
                           FROM memory_item WHERE id=%s""",
                        (r["id"],),
                    ).fetchone()
                    out.append(_memory_row(conn, row))
                return out

            return {
                "needs_review": _load(anchor_rows),
                "untrusted": _load(untrusted_rows),
            }

    @app.post("/api/review/anchor/{anchor_id}")
    def review_anchor(anchor_id: int, action: ReviewAction):
        with db.transaction() as conn:
            anchor = conn.execute(
                "SELECT id, memory_id, role, anchor_code FROM memory_anchor WHERE id=%s",
                (anchor_id,),
            ).fetchone()
            if anchor is None:
                raise HTTPException(404, "ancoră inexistentă")
            if action.action == "confirm":
                conn.execute(
                    """UPDATE memory_anchor SET resolved_by='human', confidence=1.00,
                              needs_review=false WHERE id=%s""",
                    (anchor_id,),
                )
            elif action.action == "reassign":
                if action.res_id is None:
                    raise HTTPException(422, "reassign cere res_id")
                conn.execute(
                    """UPDATE memory_anchor SET odoo_res_id=%s, resolved_by='human',
                              confidence=1.00, needs_review=false WHERE id=%s""",
                    (action.res_id, anchor_id),
                )
            elif action.action == "remove":
                conn.execute("DELETE FROM memory_anchor WHERE id=%s", (anchor_id,))
            else:
                raise HTTPException(422, "action ∈ {confirm, reassign, remove}")
            memory_id = str(anchor["memory_id"])

        # confirm/reassign pe subject declanșează chitanța DOAR în modul auto și doar
        # dacă nu există deja (plan C. Faza 2; în Faza 1 poarta rămâne manuală — A2)
        receipt_outcome = None
        if (
            action.action in ("confirm", "reassign")
            and anchor["role"] == "subject"
            and config.RECEIPT_MODE == "auto"
        ):
            try:
                receipt_outcome = receipts.post_receipt(memory_id)
            except (receipts.NoChatterTarget, AdapterError) as e:
                receipt_outcome = {"outcome": "failed", "detail": str(e)[:200]}
        return {"status": "ok", "receipt": receipt_outcome}

    @app.post("/api/reports/digest")
    def reports_digest(req: DigestRequest):
        """Digestul proactiv (etapa 9): text determinist RO din elementele netrimise.
        mark=true consemnează trimiterea (report_sent); mark=false = previzualizare."""
        from .reports.digest import build_digest

        return build_digest(mark=req.mark)

    @app.get("/api/reports/{code}")
    def report(code: str):
        from .reports.queries import REPORTS

        fn = REPORTS.get(code)
        if fn is None:
            raise HTTPException(404, f"raport necunoscut: {code}")
        return fn()

    @app.post("/api/reports/external/{normalized_text}/status")
    def external_status(normalized_text: str, req: ExternalStatus):
        if req.status not in ("dismissed", "created"):
            raise HTTPException(422, "status ∈ {dismissed, created}")
        with db.transaction() as conn:
            conn.execute(
                """INSERT INTO external_entity_status (normalized_text, status)
                   VALUES (%s, %s)
                   ON CONFLICT (normalized_text) DO UPDATE SET status = EXCLUDED.status""",
                (normalized_text, req.status),
            )
        return {"status": req.status}

    @app.post("/api/ingest/gateway")
    def ingest_gateway(req: GatewayIngest):
        """Conducta de sedimentare (etapele 3+5): chemată de hook-ul aipm-sediment.

        Poarta de intimitate se aplică SINCRON (refuzul e vizibil în răspuns);
        extracția rulează async — hook-ul nu ține gateway-ul pe loc. Conducta
        e închisă cât timp INGEST_ENABLED=false (deschiderea = decizie, P4)."""
        from .engine import privacy
        from .ingest.gateway_source import (
            ingest_gateway_async, ingest_gateway_message, source_ref_for,
        )

        if not config.INGEST_ENABLED:
            raise HTTPException(409, "conducta de sedimentare e închisă (INGEST_ENABLED=false)")
        if not req.text.strip():
            return {"status": "empty"}

        if privacy.blocked_terms(req.text):
            # consemnarea refuzului (fără conținut) se face în calea sincronă
            return ingest_gateway_message(
                req.author_key, req.text, req.chat_id, req.session_id
            )

        threading.Thread(
            target=ingest_gateway_async,
            args=(req.author_key, req.text, req.chat_id, req.session_id),
            daemon=True,
        ).start()
        return {"status": "accepted",
                "source_ref": source_ref_for(req.chat_id, req.session_id, req.text)}

    @app.post("/api/ingest/run")
    def ingest_run():
        from .ingest.chatter_poller import run_cycle

        return run_cycle(ingest_lock)

    @app.post("/api/ingest/replay")
    def ingest_replay(req: ReplayRequest):
        from .ingest.chatter_poller import replay_source

        if req.source_ref.startswith("chat:"):
            raise HTTPException(
                422, "replay indisponibil pentru chat — retrimite mesajul (uuid nou)"
            )
        with ingest_lock:
            try:
                return replay_source(req.source_ref)
            except ValueError as e:
                raise HTTPException(422, str(e))
            except LookupError as e:
                raise HTTPException(404, str(e))
            except AdapterError as e:
                raise HTTPException(502, f"Odoo indisponibil: {e}")
