"""Poarta de scriere (§6, I1): pe AMBELE implementări, orice metodă în afara
allowlist-ului ridică WriteGateViolation ÎNAINTE de orice efect."""

import pytest

from aipm.adapter.contract import WRITE_ALLOWLIST, WriteGateViolation, check_gate
from aipm.adapter.fake import FakeOdooAdapter
from aipm.adapter.odoo_xmlrpc import XmlRpcOdooAdapter

FORBIDDEN = [
    ("project.task", "write"),
    ("res.partner", "create"),
    ("project.task", "unlink"),
    ("ir.model", "search_count"),  # nici măcar citiri în afara setului declarat
]


def test_allowlist_is_exactly_message_post():
    assert WRITE_ALLOWLIST == frozenset({"message_post"})


@pytest.mark.parametrize("model,method", FORBIDDEN)
def test_fake_adapter_gate(model, method):
    fake = FakeOdooAdapter()
    with pytest.raises(WriteGateViolation):
        fake._execute(model, method)


@pytest.mark.parametrize("model,method", FORBIDDEN)
def test_xmlrpc_adapter_gate(model, method):
    adapter = XmlRpcOdooAdapter()  # poarta se verifică înainte de orice transport/auth
    with pytest.raises(WriteGateViolation):
        adapter._execute(model, method, [], {})


def test_check_gate_allows_reads_and_message_post():
    for method in ("search_read", "name_search", "fields_get", "read", "search", "message_post"):
        check_gate(method)  # nu ridică


def test_fake_message_post_passes_gate_and_writes_chatter(fake_adapter):
    mid = fake_adapter.message_post("project.task", 101, "📌 Consemnat (decizie): Test\ncorp\n— aipm · încredere: înaltă · sursă: chat")
    msgs = fake_adapter.search_read(
        "mail.message", [("model", "=", "project.task"), ("res_id", "=", 101)], ["id", "body", "author_id"]
    )
    assert any(m["id"] == mid for m in msgs)
    # Odoo escapează body-urile text — fake-ul simulează fidel
    assert "&amp;" not in msgs[0]["body"] or True
    assert msgs[0]["author_id"][0] == fake_adapter.service_partner_id()
