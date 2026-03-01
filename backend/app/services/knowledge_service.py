from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _resolve_path(path_text: str) -> Path:
    configured = Path(path_text)
    if configured.is_absolute():
        return configured

    service_file = Path(__file__).resolve()
    backend_root = service_file.parents[2]
    repo_root = service_file.parents[3]
    candidates = [
        repo_root / configured,
        backend_root / configured,
        Path.cwd() / configured,
    ]
    return candidates[0]


def _tokenize(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def _normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("id", "")).strip() or "unknown",
        "title": str(raw.get("title", "")).strip(),
        "content": str(raw.get("content", "")).strip(),
        "tags": [str(tag).strip().lower() for tag in raw.get("tags", []) if str(tag).strip()],
        "source": str(raw.get("source", "")).strip() or "knowledge_base",
        "region": str(raw.get("region", "")).strip().lower(),
    }


@lru_cache(maxsize=1)
def _load_knowledge_items() -> list[dict[str, Any]]:
    settings = get_settings()
    items: list[dict[str, Any]] = []
    for path_text in settings.knowledge_base_path_list:
        path = _resolve_path(path_text)
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, list):
            continue
        for row in payload:
            if isinstance(row, dict):
                normalized = _normalize_item(row)
                if normalized["title"] and normalized["content"]:
                    items.append(normalized)
    return items


def _score_item(query_tokens: set[str], item: dict[str, Any]) -> float:
    text = f"{item['title']} {item['content']} {' '.join(item['tags'])}".lower()
    item_tokens = _tokenize(text)
    overlap = len(query_tokens & item_tokens)
    if overlap == 0:
        return 0.0
    score = float(overlap)
    if "tamil nadu" in text or "tn" in item["tags"]:
        score += 0.8
    if item.get("region") == "tamil nadu":
        score += 0.6
    return score


def find_relevant_knowledge(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    effective_top_k = top_k or settings.knowledge_top_k
    effective_top_k = max(1, min(effective_top_k, 12))

    query_tokens = _tokenize(query)
    if not query_tokens:
        query_tokens = {"farmer"}

    scored: list[tuple[float, dict[str, Any]]] = []
    for item in _load_knowledge_items():
        score = _score_item(query_tokens, item)
        if score > 0:
            scored.append((score, item))

    if not scored:
        defaults = _load_knowledge_items()[:effective_top_k]
        return defaults

    scored.sort(key=lambda entry: entry[0], reverse=True)
    return [item for _, item in scored[:effective_top_k]]


def build_knowledge_context(query: str, *, top_k: int | None = None, max_chars: int = 2400) -> str:
    snippets = find_relevant_knowledge(query, top_k=top_k)
    if not snippets:
        return ""

    lines = ["Knowledge snippets (use as factual guidance, do not fabricate):"]
    for item in snippets:
        content = item["content"]
        if len(content) > 240:
            content = content[:237].rstrip() + "..."
        tags = ", ".join(item.get("tags", [])[:4])
        lines.append(f"- {item['title']}: {content} (tags: {tags}; source: {item['source']})")

    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 3].rstrip() + "..."
    return text
