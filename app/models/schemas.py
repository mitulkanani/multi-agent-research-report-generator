from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=8, max_length=500)
    audience: str = Field(default="General audience", min_length=2, max_length=160)
    focus_questions: list[str] = Field(default_factory=list, max_length=8)
    max_results_per_agent: int = Field(default=5, ge=1, le=10)


class SourceRecord(BaseModel):
    source_id: str | None = None
    title: str = Field(min_length=2, max_length=500)
    url: str = Field(min_length=8, max_length=2000)
    snippet: str = Field(min_length=1, max_length=6000)
    domain: str = ""
    score: float | None = None
    published_date: str | None = None
    retrieved_at: datetime
    agent_role: str
    is_demo: bool = False
    validation_notes: list[str] = Field(default_factory=list)


class AgentEvent(BaseModel):
    agent: str
    event: str
    message: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportSection(BaseModel):
    heading: str
    content: str
    citations: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    title: str
    executive_summary: str
    key_findings: list[ReportSection]
    analysis: str
    limitations: list[str]
    methodology: str
    markdown: str


class ResearchResult(BaseModel):
    run_id: str
    topic: str
    audience: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    workflow_engine: str
    research_questions: list[str]
    source_count: int
    unique_domain_count: int
    coverage_score: float
    critique: list[str]
    agent_trace: list[AgentEvent]
    sources: list[SourceRecord]
    report: ResearchReport | None = None
    error: str | None = None


class ResearchCreated(BaseModel):
    run_id: str
    status: str
    message: str
