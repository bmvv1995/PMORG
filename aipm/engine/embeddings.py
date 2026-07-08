"""Embeddings — provider-agnostic, dimensiune FIXĂ 1024 (SPEC §0).

Default: Jina v3 (decizia utilizatorului). Interfața HTTP e formatul OpenAI
(/embeddings), pe care Jina îl expune; alt provider = alt EMBED_BASE_URL/EMBED_MODEL.
"""

import logging

import httpx

from .. import config

logger = logging.getLogger(__name__)


class EmbeddingUnavailable(Exception):
    """Outage provider — insert cu embedding NULL + backfill (plan §3)."""


def embed(texts: list[str]) -> list[list[float]]:
    if not config.EMBED_API_KEY:
        raise EmbeddingUnavailable("EMBED_API_KEY nu e setat")
    try:
        resp = httpx.post(
            f"{config.EMBED_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {config.EMBED_API_KEY}"},
            json={"model": config.EMBED_MODEL, "input": texts, "dimensions": config.EMBED_DIM},
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise EmbeddingUnavailable(str(e)) from e
    data = resp.json()["data"]
    vectors = [row["embedding"] for row in sorted(data, key=lambda r: r["index"])]
    for v in vectors:
        if len(v) != config.EMBED_DIM:
            raise EmbeddingUnavailable(
                f"dimensiune {len(v)} != {config.EMBED_DIM} — providerul nu respectă contractul"
            )
    return vectors


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
