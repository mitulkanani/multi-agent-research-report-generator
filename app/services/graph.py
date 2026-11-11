from __future__ import annotations

import operator
from datetime import UTC, datetime
from typing import Annotated, TypedDict, Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.models.schemas import SourceRecord, ResearchReport, AgentEvent
from app.providers.search import SearchProvider
from app.providers.writer import DemoReportWriter

try:
    from langgraph.graph import END, START, StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:  # local lightweight fallback; install the declared dependency for LangGraph
    END = START = StateGraph = None
    LANGGRAPH_AVAILABLE = False


class ResearchState(TypedDict, total=False):
    topic: str
    audience: str
    focus_questions: list[str]
    max_results: int
    queries: dict[str, str]
    sources: Annotated[list[dict[str, Any]], operator.add]
    verified_sources: list[dict[str, Any]]
    critique: list[str]
    coverage_score: float
    unique_domain_count: int
    needs_followup: bool
    followup_query: str
    report: dict[str, Any]
    agent_trace: Annotated[list[dict[str, Any]], operator.add]


def _event(agent: str, message: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return AgentEvent(agent=agent, event="completed", message=message, timestamp=datetime.now(UTC), metadata=metadata or {}).model_dump(mode="json")


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        return ""
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    query_pairs = [
        (key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunparse((parsed.scheme.lower(), host, path, "", query, ""))


def validate_sources(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for item in raw:
        try:
            source = SourceRecord.model_validate(item)
        except Exception:
            continue
        normalized = normalize_url(source.url)
        if not normalized:
            continue
        source.url = normalized
        source.domain = source.domain.lower().removeprefix("www.") or urlparse(normalized).netloc
        if normalized not in unique:
            unique[normalized] = source.model_dump(mode="json")
    result = list(unique.values())
    result.sort(key=lambda x: (x.get("score") is not None, x.get("score") or 0), reverse=True)
    for index, source in enumerate(result, start=1):
        source["source_id"] = f"S{index}"
        notes = ["URL and required source fields passed structural validation."]
        if source.get("is_demo"):
            notes.append("Synthetic demo fixture; not a real publication.")
        source["validation_notes"] = notes
    return result


class ResearchGraph:
    def __init__(self, search_provider: SearchProvider, writer: Any, min_source_domains: int = 2) -> None:
        self.search = search_provider
        self.writer = writer
        self.min_source_domains = min_source_domains
        self.engine_name = "langgraph" if LANGGRAPH_AVAILABLE else "sequential_fallback"
        self.compiled = self._build_graph() if LANGGRAPH_AVAILABLE else None

    def _plan(self, state: ResearchState) -> ResearchState:
        topic = state["topic"].strip()
        questions = state.get("focus_questions", [])
        queries = {
            "evidence_scout": topic,
            "counterpoint_analyst": f"{topic} limitations criticisms risks tradeoffs",
            "context_researcher": f"{topic} background industry context recent developments",
        }
        if questions:
            queries["evidence_scout"] = f"{topic} {questions[0]}"
        return {"queries": queries, "agent_trace": [_event("planner", "Decomposed the topic into three research angles.", {"query_count": 3})]}

    def _research_node(self, role: str):
        def run(state: ResearchState) -> ResearchState:
            query = state["queries"][role]
            sources = self.search.search(query, role=role, limit=state.get("max_results", 5))
            return {"sources": [s.model_dump(mode="json") for s in sources],
                    "agent_trace": [_event(role, f"Retrieved {len(sources)} source records.", {"query": query})]}
        return run

    def _verify(self, state: ResearchState) -> ResearchState:
        valid = validate_sources(state.get("sources", []))
        domains = {s["domain"] for s in valid}
        count_score = min(len(valid) / 6, 1.0)
        diversity_score = min(len(domains) / max(self.min_source_domains, 1), 1.0)
        coverage = round((count_score * 0.55 + diversity_score * 0.45) * 100, 1)
        return {"verified_sources": valid, "unique_domain_count": len(domains), "coverage_score": coverage,
                "agent_trace": [_event("evidence_verifier", f"Validated {len(valid)} unique source records across {len(domains)} domains.", {"coverage_score": coverage})]}

    def _critic(self, state: ResearchState) -> ResearchState:
        notes: list[str] = []
        if len(state.get("verified_sources", [])) < 3:
            notes.append("Fewer than three unique sources were available; conclusions should be considered preliminary.")
        if state.get("unique_domain_count", 0) < self.min_source_domains:
            notes.append("Source-domain diversity is below the configured target; seek independent perspectives.")
        if not state.get("focus_questions"):
            notes.append("No specific focus questions were supplied; coverage is based on the broad topic only.")
        needs = len(state.get("verified_sources", [])) < 3 or state.get("unique_domain_count", 0) < self.min_source_domains
        query = f"{state['topic']} independent sources evidence case studies data"
        return {"critique": notes, "needs_followup": needs, "followup_query": query,
                "agent_trace": [_event("critic", "Reviewed evidence breadth and source diversity.", {"needs_followup": needs, "notes": len(notes)})]}

    def _followup(self, state: ResearchState) -> ResearchState:
        if not state.get("needs_followup"):
            return {"sources": []}
        results = self.search.search(state.get("followup_query", state["topic"]), role="followup_researcher", limit=state.get("max_results", 5))
        return {"sources": [s.model_dump(mode="json") for s in results],
                "agent_trace": [_event("followup_researcher", f"Collected {len(results)} follow-up source records.")]}

    def _write(self, state: ResearchState) -> ResearchState:
        sources = [SourceRecord.model_validate(s) for s in state.get("verified_sources", [])]
        # If follow-up sources changed the source list, the verifier ran again before this node.
        report = self.writer.write(topic=state["topic"], audience=state.get("audience", "General audience"),
            questions=state.get("focus_questions", []), sources=sources, critique=state.get("critique", []))
        return {"report": report.model_dump(mode="json"),
                "agent_trace": [_event("report_writer", "Generated a report with evidence IDs and limitations.", {"source_count": len(sources)})]}

    def _build_graph(self):
        graph = StateGraph(ResearchState)
        graph.add_node("planner", self._plan)
        graph.add_node("evidence_scout", self._research_node("evidence_scout"))
        graph.add_node("counterpoint_analyst", self._research_node("counterpoint_analyst"))
        graph.add_node("context_researcher", self._research_node("context_researcher"))
        graph.add_node("verifier", self._verify)
        graph.add_node("critic", self._critic)
        graph.add_node("followup_researcher", self._followup)
        graph.add_node("verifier_after_followup", self._verify)
        graph.add_node("report_writer", self._write)
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "evidence_scout")
        graph.add_edge("planner", "counterpoint_analyst")
        graph.add_edge("planner", "context_researcher")
        graph.add_edge(["evidence_scout", "counterpoint_analyst", "context_researcher"], "verifier")
        graph.add_edge("verifier", "critic")
        graph.add_conditional_edges("critic", lambda s: "followup" if s.get("needs_followup") else "write",
            {"followup": "followup_researcher", "write": "report_writer"})
        graph.add_edge("followup_researcher", "verifier_after_followup")
        graph.add_edge("verifier_after_followup", "report_writer")
        graph.add_edge("report_writer", END)
        return graph.compile()

    def run(self, *, topic: str, audience: str, focus_questions: list[str], max_results: int) -> dict[str, Any]:
        initial: ResearchState = {"topic": topic, "audience": audience, "focus_questions": focus_questions,
            "max_results": max_results, "sources": [], "agent_trace": []}
        if self.compiled is not None:
            return self.compiled.invoke(initial)
        # Dependency-free fallback mirrors the same explicit agent stages for local tests.
        state: ResearchState = dict(initial)

        def apply(update: ResearchState) -> None:
            for key, value in update.items():
                if key in {"sources", "agent_trace"}:
                    state[key] = state.get(key, []) + value
                else:
                    state[key] = value

        apply(self._plan(state))
        for role in ("evidence_scout", "counterpoint_analyst", "context_researcher"):
            apply(self._research_node(role)(state))
        apply(self._verify(state))
        apply(self._critic(state))
        if state.get("needs_followup"):
            apply(self._followup(state))
            apply(self._verify(state))
        apply(self._write(state))
        return state
