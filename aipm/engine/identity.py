"""Vama — lookup-ul determinist al identității (PLAN-INTEGRARE etapa 2, D1).

Cine e parte la conversație se identifică prin identity_map, nu prin ghicire:
cheie mapată → autor fixat fără niciun apel LLM; cheie nemapată → gol de
cunoaștere înregistrat (external_entity), niciodată identitate inventată.
Tabelele se scriu doar prin migrare — aici sunt exclusiv citite.
"""

import dataclasses
import logging

logger = logging.getLogger(__name__)

KNOWN_CHANNELS = ("telegram",)


@dataclasses.dataclass
class MappedIdentity:
    channel: str
    channel_id: str
    partner_res_id: int | None
    employee_res_id: int | None
    display_name: str


def parse_author_key(author_key: str) -> tuple[str, str] | None:
    """'telegram:12345' → ('telegram', '12345'); formă necunoscută → None."""
    if not author_key or ":" not in author_key:
        return None
    channel, _, channel_id = author_key.partition(":")
    if channel not in KNOWN_CHANNELS or not channel_id.strip():
        return None
    return channel, channel_id.strip()


def resolve_author(conn, author_key: str) -> MappedIdentity | None:
    parsed = parse_author_key(author_key)
    if parsed is None:
        return None
    channel, channel_id = parsed
    row = conn.execute(
        """SELECT channel, channel_id, partner_res_id, employee_res_id, display_name
           FROM identity_map WHERE channel=%s AND channel_id=%s""",
        (channel, channel_id),
    ).fetchone()
    if row is None:
        return None
    return MappedIdentity(**dict(row))


def resolve_board(conn, board_slug: str) -> int | None:
    row = conn.execute(
        "SELECT project_res_id FROM project_map WHERE board_slug=%s", (board_slug,)
    ).fetchone()
    return row["project_res_id"] if row else None


def unknown_author_text(author_key: str) -> str:
    """Cheia golului de cunoaștere pentru un autor nemapat (external_entity)."""
    return f"autor:{author_key}".lower()


def record_unknown_author(conn, author_key: str, memory_ids: list[str]) -> None:
    """Golul, nu invenția: autorul nemapat devine entitate externă înregistrată."""
    text = unknown_author_text(author_key)
    conn.execute(
        "INSERT INTO external_entity_status (normalized_text) VALUES (%s) ON CONFLICT DO NOTHING",
        (text,),
    )
    for memory_id in memory_ids:
        conn.execute(
            "INSERT INTO external_entity_mention (normalized_text, memory_id) VALUES (%s, %s)",
            (text, memory_id),
        )
