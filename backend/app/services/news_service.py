from __future__ import annotations

from datetime import UTC, datetime
from xml.etree import ElementTree

import httpx


GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=Tamil+Nadu+agriculture+farmer+crop&hl=en-IN&gl=IN&ceid=IN:en"
)

FALLBACK_NEWS = [
    {
        "title": "Tamil Nadu farmers prepare for seasonal crop planning",
        "summary": "Use local rainfall, soil, and market conditions before selecting crop combinations.",
        "url": "https://www.tn.gov.in/",
        "source": "Tamil Nadu Government",
        "published_at": datetime.now(UTC).isoformat(),
        "image_url": "",
    },
    {
        "title": "Water-saving irrigation remains key for dry belts",
        "summary": "Drip and sprinkler methods continue to improve water-use efficiency across districts.",
        "url": "https://www.agritech.tnau.ac.in/",
        "source": "TNAU",
        "published_at": datetime.now(UTC).isoformat(),
        "image_url": "",
    },
    {
        "title": "District-wise crop advisories help reduce risk",
        "summary": "Regional advisories can improve fertilizer timing and yield stability.",
        "url": "https://agriwelfare.gov.in/",
        "source": "Agri Welfare",
        "published_at": datetime.now(UTC).isoformat(),
        "image_url": "",
    },
]


def _safe_text(element: ElementTree.Element | None, default: str = "") -> str:
    if element is None or element.text is None:
        return default
    return element.text.strip()


def _extract_source(item: ElementTree.Element) -> str:
    for child in item:
        if child.tag.endswith("source"):
            return _safe_text(child, "News")
    return "News"


def _extract_image_url(item: ElementTree.Element) -> str:
    for child in item:
        if child.tag.endswith("thumbnail"):
            return (child.attrib or {}).get("url", "")
    return ""


async def fetch_tamil_nadu_agri_news(limit: int = 9) -> list[dict]:
    effective_limit = max(3, min(limit, 15))
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(GOOGLE_NEWS_RSS_URL)
            response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        channel = root.find("channel")
        items = [] if channel is None else channel.findall("item")

        parsed: list[dict] = []
        for item in items[:effective_limit]:
            title = _safe_text(item.find("title"), "Agriculture Update")
            url = _safe_text(item.find("link"), "")
            description = _safe_text(item.find("description"), "")
            published = _safe_text(item.find("pubDate"), datetime.now(UTC).isoformat())
            parsed.append(
                {
                    "title": title,
                    "summary": description or "Latest agriculture update for Tamil Nadu farmers.",
                    "url": url,
                    "source": _extract_source(item),
                    "published_at": published,
                    "image_url": _extract_image_url(item),
                }
            )
        if parsed:
            return parsed
    except Exception:
        pass
    return FALLBACK_NEWS[:effective_limit]
