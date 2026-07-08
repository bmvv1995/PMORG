"""Rapoartele §7 — pe date sintetice (plan §D Faza 3)."""

from datetime import date, timedelta

from aipm.reports import queries

from .helpers import insert_anchor, insert_item


def test_due_soon_includes_overdue_sorted(clean_db, fake_adapter):
    today = date(2026, 7, 7)
    with clean_db.transaction() as conn:
        conn.execute("SELECT set_config('aipm.today', %s, false)", (str(today),))
        insert_item(conn, kind="commitment", title="Depășit", body="b",
                    due_at=today - timedelta(days=2), source_ref="c:1", content_hash="r1")
        insert_item(conn, kind="commitment", title="Aproape", body="b",
                    due_at=today + timedelta(days=2), source_ref="c:2", content_hash="r2")
        insert_item(conn, kind="commitment", title="Departe", body="b",
                    due_at=today + timedelta(days=30), source_ref="c:3", content_hash="r3")
    report = queries.due_soon()
    titles = [i["title"] for i in report["items"]]
    assert "Departe" not in titles
    assert titles == ["Depășit", "Aproape"]


def test_commitments_missing_two_lists(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        no_due = insert_item(conn, kind="commitment", title="Fără termen", body="b",
                             source_ref="c:4", content_hash="r4")
        insert_anchor(conn, no_due, role="owner", anchor_code="PARTNER", res_id=202)
        insert_item(conn, kind="commitment", title="Fără responsabil", body="b",
                    due_at=date(2026, 8, 1), source_ref="c:5", content_hash="r5")
    report = queries.commitments_missing()
    assert [i["title"] for i in report["missing_due"]] == ["Fără termen"]
    assert [i["title"] for i in report["missing_owner"]] == ["Fără responsabil"]


def test_stale_questions(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        insert_item(conn, kind="open_question", title="Veche", body="b",
                    source_ref="c:6", content_hash="r6",
                    created_at="2026-06-01T10:00:00+00:00")
        insert_item(conn, kind="open_question", title="Nouă", body="b",
                    source_ref="c:7", content_hash="r7")
    report = queries.stale_questions()
    assert [i["title"] for i in report["items"]] == ["Veche"]


def test_external_recurring_threshold_and_status(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        for i in range(3):
            mid = insert_item(conn, title=f"Obs {i}", body="b",
                              source_ref=f"c:e{i}", content_hash=f"re{i}")
            conn.execute(
                "INSERT INTO external_entity_mention (normalized_text, memory_id) VALUES (%s,%s)",
                ("primaria chisinau", mid),
            )
        mid2 = insert_item(conn, title="Obs singulară", body="b",
                           source_ref="c:e9", content_hash="re9")
        conn.execute(
            "INSERT INTO external_entity_mention (normalized_text, memory_id) VALUES (%s,%s)",
            ("firma de decor", mid2),
        )
    report = queries.external_recurring()
    assert [i["normalized_text"] for i in report["items"]] == ["primaria chisinau"]

    with clean_db.transaction() as conn:
        conn.execute(
            """INSERT INTO external_entity_status (normalized_text, status)
               VALUES ('primaria chisinau', 'created')
               ON CONFLICT (normalized_text) DO UPDATE SET status='created'"""
        )
    assert queries.external_recurring()["items"] == []
