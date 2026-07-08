"""LLM wrapper — un singur loc pentru toate apelurile (portat din nous).

Provider-agnostic prin env: LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
(azi DeepSeek pe endpoint format-Anthropic; se schimbă doar base_url).
LangSmith opțional: activ doar dacă pachetul există și LANGSMITH_API_KEY e setat.

Roluri trasate separat: llm_extract, llm_query_entities, llm_rescore, llm_narrate.
"""

import logging
import os

import anthropic

from .. import config

logger = logging.getLogger(__name__)

_client = None

try:  # LangSmith = opțional prin env (decizia utilizatorului)
    if os.environ.get("LANGSMITH_API_KEY"):
        from langsmith import traceable
        from langsmith.wrappers import wrap_anthropic
    else:
        raise ImportError
except ImportError:

    def traceable(name: str):
        def deco(fn):
            return fn

        return deco

    def wrap_anthropic(client):
        return client


class LLMTransientError(Exception):
    """Timeout / 5xx / rate-limit — mesajul rămâne reprocesabil (plan §3 pasul 2)."""


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        kwargs = {"api_key": config.LLM_API_KEY}
        if config.LLM_BASE_URL:
            kwargs["base_url"] = config.LLM_BASE_URL
        _client = wrap_anthropic(anthropic.Anthropic(**kwargs))
        logger.info(
            "LLM client: model=%s base_url=%s",
            config.LLM_MODEL,
            config.LLM_BASE_URL or "default(anthropic)",
        )
    return _client


def _call(role: str, system: str, user: str, max_tokens: int) -> str:
    try:
        resp = get_client().messages.create(
            model=config.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except (
        anthropic.APIConnectionError,
        anthropic.APITimeoutError,
        anthropic.RateLimitError,
        anthropic.InternalServerError,
    ) as e:
        raise LLMTransientError(f"{role}: {e}") from e
    for block in resp.content:
        if hasattr(block, "text"):
            return block.text
    return ""


_JSON_SUFFIX = "\n\nRăspunde DOAR cu JSON valid. Fără markdown, fără explicații."


@traceable(name="llm_extract")
def extract_json(system: str, user: str) -> str:
    return _call("llm_extract", system + _JSON_SUFFIX, user, 4096) or "{}"


@traceable(name="llm_query_entities")
def query_entities_json(system: str, user: str) -> str:
    return _call("llm_query_entities", system + _JSON_SUFFIX, user, 1024) or "{}"


@traceable(name="llm_rescore")
def rescore_json(system: str, user: str) -> str:
    return _call("llm_rescore", system + _JSON_SUFFIX, user, 2048) or "{}"


@traceable(name="llm_narrate")
def narrate_json(system: str, user: str) -> str:
    return _call("llm_narrate", system + _JSON_SUFFIX, user, 2048) or "{}"
