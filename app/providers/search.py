from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlparse

from app.models.schemas import SourceRecord


class SearchProvider(Protocol):
    def search(self, query: str, *, role: str, limit: int) -> list[SourceRecord]: ...


class DemoSearchProvider:
    """Deterministic synthetic evidence for local development and CI only."""

    DOMAINS = ["research-demo.example", "industry-demo.example", "engineering-demo.example"]

    def search(self, query: str, *, role: str, limit: int) -> list[SourceRecord]:
        now = datetime.now(UTC)
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:70] or "topic"
        records = []
        for index, domain in enumerate(self.DOMAINS[:max(1, min(limit, 3))], start=1):
            records.append(SourceRecord(
                title=f"Synthetic demo evidence {index}: {query[:100]}",
                url=f"https://{domain}/demo/{slug}/{index}",
                snippet=(
                    f"This is a synthetic fixture for testing the {role} research agent. "
                    f"It demonstrates how retrieved evidence about '{query}' is stored, "
                    "reviewed, cited, and included in a report. It is not a real publication "
                    "and contains no independently verified research finding."
                ),
                domain=domain, score=0.95 - (index * 0.07), published_date="2026-01-15",
                retrieved_at=now, agent_role=role, is_demo=True,
            ))
        return records


class TavilySearchProvider:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.getenv("TAVILY_API_KEY", "")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is required for live search.")
        try:
            from tavily import TavilyClient
        except ImportError as exc:
            raise RuntimeError("Install the search extra: pip install -e '.[search]'.") from exc
        self.client = TavilyClient(api_key=key)

    def search(self, query: str, *, role: str, limit: int) -> list[SourceRecord]:
        response = self.client.search(query=query, max_results=limit, search_depth="advanced")
        now = datetime.now(UTC)
        output: list[SourceRecord] = []
        for item in response.get("results", []):
            url = str(item.get("url", "")).strip()
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            output.append(SourceRecord(
                title=str(item.get("title") or parsed.netloc)[:500],
                url=url[:2000],
                snippet=str(item.get("content") or "No snippet returned by search provider.")[:6000],
                domain=parsed.netloc.lower().removeprefix("www."),
                score=float(item["score"]) if item.get("score") is not None else None,
                published_date=item.get("published_date"), retrieved_at=now,
                agent_role=role, is_demo=False,
            ))
        return output


def build_search_provider(provider: str, api_key: str = "") -> SearchProvider:
    if provider == "tavily":
        return TavilySearchProvider(api_key)
    return DemoSearchProvider()
