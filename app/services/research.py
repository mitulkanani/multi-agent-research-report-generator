from datetime import UTC, datetime
from uuid import uuid4
from typing import Any

from app.core.config import settings
from app.models.schemas import ResearchRequest, ResearchResult, ResearchReport, SourceRecord, AgentEvent
from app.providers.search import build_search_provider
from app.providers.writer import build_writer
from app.services.graph import ResearchGraph
from app.services.repository import ResearchRepository


class ResearchService:
    def __init__(self, repository: ResearchRepository | None = None, search_provider=None, writer=None) -> None:
        self.repository = repository or ResearchRepository(settings.database_path)
        self.search_provider = search_provider or build_search_provider(settings.search_provider, settings.tavily_api_key)
        self.writer = writer or build_writer(settings.llm_provider, settings.openai_api_key, settings.openai_model)
        self.graph = ResearchGraph(self.search_provider, self.writer, settings.min_source_domains)

    def run(self, request: ResearchRequest) -> ResearchResult:
        run_id = str(uuid4())
        created = datetime.now(UTC)
        try:
            state = self.graph.run(topic=request.topic, audience=request.audience,
                focus_questions=request.focus_questions, max_results=request.max_results_per_agent)
            completed = datetime.now(UTC)
            sources = [SourceRecord.model_validate(item) for item in state.get("verified_sources", [])]
            report = ResearchReport.model_validate(state["report"])
            trace = [AgentEvent.model_validate(item) for item in state.get("agent_trace", [])]
            result = ResearchResult(run_id=run_id, topic=request.topic, audience=request.audience, status="completed",
                created_at=created, completed_at=completed, workflow_engine=self.graph.engine_name,
                research_questions=state.get("focus_questions", []), source_count=len(sources),
                unique_domain_count=state.get("unique_domain_count", 0), coverage_score=state.get("coverage_score", 0),
                critique=state.get("critique", []), agent_trace=trace, sources=sources, report=report)
        except Exception as exc:
            completed = datetime.now(UTC)
            result = ResearchResult(run_id=run_id, topic=request.topic, audience=request.audience, status="failed",
                created_at=created, completed_at=completed, workflow_engine=self.graph.engine_name,
                research_questions=request.focus_questions, source_count=0, unique_domain_count=0, coverage_score=0,
                critique=[], agent_trace=[], sources=[], error=f"{type(exc).__name__}: {exc}")
        self.repository.save(result.run_id, result.topic, result.status, result.created_at.isoformat(),
            result.completed_at.isoformat() if result.completed_at else None, result.model_dump(mode="json"))
        return result

    def get(self, run_id: str) -> ResearchResult | None:
        data = self.repository.get(run_id)
        return ResearchResult.model_validate(data) if data else None

    def list(self, limit: int = 20) -> list[ResearchResult]:
        return [ResearchResult.model_validate(item) for item in self.repository.list(limit)]
