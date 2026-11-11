from datetime import UTC, datetime

from app.models.schemas import ResearchRequest
from app.providers.search import DemoSearchProvider
from app.providers.writer import DemoReportWriter
from app.services.graph import ResearchGraph, normalize_url, validate_sources


def test_demo_graph_runs_all_research_roles_and_writes_report():
    graph = ResearchGraph(DemoSearchProvider(), DemoReportWriter(), min_source_domains=2)
    state = graph.run(
        topic="Enterprise adoption of RAG systems",
        audience="Technology leaders",
        focus_questions=["What architectures are used?", "How is quality evaluated?"],
        max_results=5,
    )
    assert state["report"]["title"].startswith("Research Report:")
    assert len(state["verified_sources"]) >= 3
    roles = {s["agent_role"] for s in state["verified_sources"]}
    assert {"evidence_scout", "counterpoint_analyst", "context_researcher"}.issubset(roles)
    assert any(event["agent"] == "critic" for event in state["agent_trace"])
    assert any(event["agent"] == "report_writer" for event in state["agent_trace"])


def test_sources_are_deduplicated_and_assigned_stable_ids():
    base = {
        "title": "Example source", "url": "https://www.example.com/report/?utm_source=test",
        "snippet": "A sufficiently detailed source snippet.", "domain": "www.example.com",
        "score": 0.8, "retrieved_at": datetime.now(UTC), "agent_role": "evidence_scout",
    }
    sources = validate_sources([base, {**base, "url": "https://example.com/report"}])
    assert len(sources) == 1
    assert sources[0]["source_id"] == "S1"
    assert sources[0]["url"] == "https://example.com/report"


def test_sources_reject_non_http_urls():
    base = {
        "title": "Bad source", "url": "javascript:alert(1)", "snippet": "Some snippet.",
        "domain": "evil.invalid", "retrieved_at": datetime.now(UTC), "agent_role": "researcher",
    }
    assert validate_sources([base]) == []


def test_url_normalization_drops_tracking_parameters():
    assert normalize_url("https://www.example.com/a?utm_campaign=x#section") == "https://example.com/a"


def test_critic_triggers_a_bounded_followup_when_domain_target_is_high():
    graph = ResearchGraph(DemoSearchProvider(), DemoReportWriter(), min_source_domains=5)
    state = graph.run(
        topic="Enterprise AI research governance",
        audience="Risk leaders",
        focus_questions=["What controls are recommended?"],
        max_results=5,
    )
    agents = [event["agent"] for event in state["agent_trace"]]
    assert "critic" in agents
    assert "followup_researcher" in agents
    assert agents.count("followup_researcher") == 1
    assert state["report"]["markdown"]


def test_url_normalization_preserves_functional_query_parameters():
    assert normalize_url("https://www.example.com/search?q=rag&utm_source=news") == "https://example.com/search?q=rag"
