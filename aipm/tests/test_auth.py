"""Auth (§8): /api/* fără token → 401; /api/health rămâne liber; token corect → 200."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, clean_db, fake_adapter):
    from aipm import config

    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    from aipm.main import app

    # fără lifespan: nu pornim ingest_loop în teste de auth
    return TestClient(app)


def test_health_is_open(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_api_requires_token(client):
    assert client.get("/api/anchors/types").status_code == 401
    assert client.get("/api/rules").status_code == 401


def test_wrong_token_rejected(client):
    resp = client.get("/api/anchors/types", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_bearer_token_accepted(client):
    resp = client.get("/api/anchors/types", headers={"Authorization": "Bearer secret-token"})
    assert resp.status_code == 200
    types = {t["code"] for t in resp.json()["anchor_types"]}
    assert types == {
        "COMPANY", "PROJECT", "TASK", "PARTNER", "EMPLOYEE",
        "PURCHASE_ORDER", "SALE_ORDER", "LEAD", "PRODUCT",
        "INITIATIVE", "IDENTITY",  # migrația 0008 (convergența v2, S3)
    }


def test_cookie_token_accepted(client):
    client.cookies.set("aipm_token", "secret-token")
    assert client.get("/api/rules").status_code == 200
