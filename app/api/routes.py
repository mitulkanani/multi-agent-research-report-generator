from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.models.schemas import ResearchRequest, ResearchCreated, ResearchResult
from app.services.research import ResearchService

router = APIRouter(prefix="/api/research", tags=["research"])
service = ResearchService()


@router.post("", response_model=ResearchResult, status_code=201)
def create_research(payload: ResearchRequest) -> ResearchResult:
    result = service.run(payload)
    if result.status != "completed":
        raise HTTPException(status_code=502, detail={"run_id": result.run_id, "error": result.error})
    return result


@router.get("", response_model=list[ResearchResult])
def list_research(limit: int = Query(default=20, ge=1, le=100)) -> list[ResearchResult]:
    return service.list(limit)


@router.get("/{run_id}", response_model=ResearchResult)
def get_research(run_id: str) -> ResearchResult:
    result = service.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return result


@router.get("/{run_id}/markdown", response_class=PlainTextResponse)
def get_markdown(run_id: str) -> str:
    result = service.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research run not found.")
    if not result.report:
        raise HTTPException(status_code=409, detail="Report is not available.")
    return result.report.markdown
