"""AI-PM — serviciul FastAPI (plan §8).

Expunere: bind 127.0.0.1 + Bearer/cookie auth (exceptat GET /api/health).
Acces remote v1 = tunel SSH. Pornire: python -m aipm.main
"""

import asyncio
import logging
import pathlib

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from . import config, db
from .adapter import get_adapter
from .adapter.contract import AdapterError
from .ingest import ingest_lock

logger = logging.getLogger(__name__)

WEB_DIR = pathlib.Path(__file__).parent / "web"


async def _ingest_loop():
    from .ingest.chatter_poller import run_cycle

    while True:
        try:
            await asyncio.to_thread(run_cycle, ingest_lock)
        except Exception:
            logger.exception("ciclul de ingest a eșuat; reiau la următorul tick")
        await asyncio.sleep(config.CHATTER_POLL_SECONDS)


async def _lifespan(app: FastAPI):
    task = asyncio.create_task(_ingest_loop())
    yield
    task.cancel()
    db.close_pool()


app = FastAPI(title="AI-PM", lifespan=_lifespan)


# --- Auth: Bearer token sau cookie; GET /api/health e singura excepție (plan §8) ---
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path == "/api/health" and request.method == "GET":
        return await call_next(request)
    token = config.AIPM_AUTH_TOKEN
    if token:
        supplied = ""
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            supplied = auth_header[7:]
        elif "aipm_token" in request.cookies:
            supplied = request.cookies["aipm_token"]
        elif request.url.path == "/" and request.query_params.get("token"):
            supplied = request.query_params["token"]
        if supplied != token:
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
    response = await call_next(request)
    # setează cookie-ul la prima vizită cu ?token= (UI-ul browserului)
    if token and request.url.path == "/" and request.query_params.get("token") == token:
        response.set_cookie("aipm_token", token, httponly=True, samesite="strict")
    return response


def _static(response: Response) -> Response:
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.get("/api/health")
def health():
    out = {
        "pg": False,
        "odoo": False,
        "llm_key_set": bool(config.LLM_API_KEY),
        "embed_ok": bool(config.EMBED_API_KEY),
        "cursor_lag": None,
        "adapter_impl": config.ODOO_ADAPTER,
    }
    try:
        with db.transaction() as conn:
            conn.execute("SELECT 1")
            row = conn.execute(
                "SELECT last_message_id, updated_at FROM ingest_cursor WHERE source_type='chatter'"
            ).fetchone()
            out["pg"] = True
            out["cursor_lag"] = None if row is None else str(row["updated_at"])
    except Exception as e:
        out["pg_error"] = str(e)
    try:
        get_adapter().schema("res.company")
        out["odoo"] = True
    except AdapterError as e:
        out["odoo_error"] = str(e)
    return out


@app.get("/api/anchors/types")
def anchor_types():
    with db.transaction() as conn:
        rows = conn.execute(
            """SELECT code, odoo_model, label_ro, resolution_fields, disambiguation_fields,
                      has_chatter, url_template, accept_threshold, review_threshold, active
               FROM anchor_type ORDER BY code"""
        ).fetchall()
    return {"anchor_types": [dict(r) for r in rows]}


@app.get("/api/rules")
def rules():
    with db.transaction() as conn:
        rows = conn.execute(
            "SELECT code, body_ro, status, version, approved_by, approved_at FROM rule ORDER BY code"
        ).fetchall()
    return {"rules": [dict(r) | {"approved_at": str(r["approved_at"])} for r in rows]}


# Rutele /api de conversație/memorie/review/rapoarte/ingest se înregistrează în api_routes
from . import api_routes  # noqa: E402  (înregistrează endpoint-urile pe `app`)

api_routes.register(app)


@app.get("/")
def index():
    return _static(FileResponse(WEB_DIR / "chat.html"))


@app.get("/review")
def review_page():
    return _static(FileResponse(WEB_DIR / "review.html"))


@app.get("/reports")
def reports_page():
    return _static(FileResponse(WEB_DIR / "reports.html"))


@app.get("/web/{filename}")
def web_asset(filename: str):
    path = (WEB_DIR / filename).resolve()
    if path.parent != WEB_DIR.resolve() or not path.exists():
        return JSONResponse({"detail": "not found"}, status_code=404)
    return _static(FileResponse(path))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.AIPM_BIND, port=config.AIPM_PORT)
