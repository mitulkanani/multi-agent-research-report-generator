from app.models.schemas import ResearchRequest
from app.providers.search import DemoSearchProvider
from app.providers.writer import DemoReportWriter
from app.services.repository import ResearchRepository
from app.services.research import ResearchService


def make_service(tmp_path):
    repo = ResearchRepository(str(tmp_path / "research.sqlite3"))
    return ResearchService(repo, DemoSearchProvider(), DemoReportWriter())


def test_research_run_is_persisted_and_retrievable(tmp_path):
    service = make_service(tmp_path)
    result = service.run(ResearchRequest(
        topic="Enterprise adoption of RAG systems",
        audience="Engineering leadership",
        focus_questions=["What are the architecture patterns?"],
    ))
    assert result.status == "completed"
    assert result.report is not None
    assert result.source_count == len(result.sources)
    loaded = service.get(result.run_id)
    assert loaded is not None
    assert loaded.report.markdown == result.report.markdown

def test_research_history_lists_newest_first(tmp_path):
    service = make_service(tmp_path)
    first = service.run(ResearchRequest(topic="First research topic", audience="Analysts"))
    second = service.run(ResearchRequest(topic="Second research topic", audience="Analysts"))
    ids = [item.run_id for item in service.list(10)]
    assert ids[0] == second.run_id
    assert first.run_id in ids
