"""Load Automat documentation sections for Telegram (from Wiki markdown)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from config_loader import wiki_root

_MARKER = re.compile(r"<!--\s*telegram:(\w+)\s*-->")
_SECTION_HEADING = re.compile(r"^##\s+(.+)$", re.MULTILINE)

DOC_REL_PATH = (
    "06-Стратегии автоматизированной LLM торговли/Automat_documentation.md"
)

SECTION_LABELS: dict[str, str] = {
    "overview": "Обзор",
    "pipeline": "Конвейер",
    "crypto": "Крипто",
    "moex": "MOEX",
    "wiki_map": "Wiki→код",
    "bot_menu": "Меню бота",
}


def _doc_path():
    return wiki_root() / DOC_REL_PATH


def _strip_wiki_links(text: str) -> str:
    """[[Link]] → Link for plain Telegram text."""
    return re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)


def _strip_html_entities_for_tg(text: str) -> str:
    return text.replace("&lt;", "<").replace("&gt;", ">")


@lru_cache(maxsize=1)
def _parse_sections() -> dict[str, dict[str, str]]:
    path = _doc_path()
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8")
    sections: dict[str, dict[str, str]] = {}
    markers = list(_MARKER.finditer(raw))

    for i, match in enumerate(markers):
        section_id = match.group(1)
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(raw)
        chunk = raw[start:end].strip()
        heading = SECTION_LABELS.get(section_id, section_id)
        hm = _SECTION_HEADING.search(chunk)
        if hm:
            heading = hm.group(1).strip()
            chunk = chunk[hm.end() :].strip()
        body = _strip_html_entities_for_tg(_strip_wiki_links(chunk))
        sections[section_id] = {"id": section_id, "title": heading, "body": body}

    return sections


def list_automat_doc_sections() -> list[dict[str, str]]:
    sections = _parse_sections()
    order = ["overview", "pipeline", "crypto", "moex", "wiki_map", "bot_menu"]
    result: list[dict[str, str]] = []
    for sid in order:
        if sid in sections:
            result.append({"id": sid, "title": sections[sid]["title"]})
    for sid, data in sections.items():
        if sid not in order:
            result.append({"id": sid, "title": data["title"]})
    return result


def get_automat_doc_section(section_id: str) -> dict[str, Any]:
    sections = _parse_sections()
    if section_id not in sections:
        return {
            "id": section_id,
            "title": "Не найдено",
            "body": f"Раздел «{section_id}» отсутствует. Проверьте {DOC_REL_PATH}.",
            "sections": list_automat_doc_sections(),
        }
    data = sections[section_id]
    return {
        "id": data["id"],
        "title": data["title"],
        "body": data["body"],
        "sections": list_automat_doc_sections(),
        "source": str(_doc_path()),
    }


def get_automat_docs_index() -> dict[str, Any]:
    return {
        "sections": list_automat_doc_sections(),
        "source": str(_doc_path()),
        "default_section": "overview",
    }
