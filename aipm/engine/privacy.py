"""Poarta de intimitate (PLAN-INTEGRARE etapa 4, decizia D2) — deterministă.

Lista „niciodată la AI" e a ownerului: un fișier text, un termen pe linie
(versionat în git-ul organizației — P5). Potrivirea acoperă formele flexionate
românești prin pliere de diacritice + potrivire pe prefix de cuvânt
(salariu → salariului, salariile); expresiile multi-cuvânt se potrivesc ca
subșir pliat. Determinist prin construcție: fără LLM, fără stare —
aceleași intrări dau întotdeauna același rezultat (T10).

Refuzul se consemnează FĂRĂ conținut și FĂRĂ termenii atinși — jurnalul
nu are voie să re-scape exact ce a oprit.
"""

import os
import re
import unicodedata

from .. import config

_MIN_PREFIX = 4  # sub 4 litere doar potrivire exactă (altfel "ion" ar opri tot)


def fold(text: str) -> str:
    """minuscule + pliere diacritice — aceeași normalizare pe listă și pe text."""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if not unicodedata.combining(c))


def load_denylist(path: str | None = None) -> list[str]:
    path = config.PRIVACY_DENYLIST_FILE if path is None else path
    if not path or not os.path.exists(path):
        return []
    terms = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(fold(line))
    return terms


def blocked_terms(text: str, terms: list[str] | None = None) -> list[str]:
    """Termenii din listă prezenți în text (normalizat). Listă goală = trece."""
    if terms is None:
        terms = load_denylist()
    if not terms:
        return []
    folded = fold(text)
    words = re.findall(r"\w+", folded, re.UNICODE)
    hits = []
    for t in terms:
        if " " in t:
            if t in folded:
                hits.append(t)
        elif any(w == t or (len(t) >= _MIN_PREFIX and w.startswith(t)) for w in words):
            hits.append(t)
    return hits
