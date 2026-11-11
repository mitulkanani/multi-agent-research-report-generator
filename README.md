# Multi-Agent Research & Report Generator

A research assistant built around a **planner → parallel research agents → evidence verifier → critic → report writer** workflow. It produces a structured report with an inspectable evidence ledger, source links, limitations, and explicit citation markers.

> **Scope and honesty:** the deterministic demo provider uses synthetic fixture sources and is intended for local development/testing. Live web research uses Tavily, and optional report synthesis uses OpenAI. Source validation checks structure, URLs, duplicates, and domain diversity; it does not prove that a source is truthful or that a claim is independently verified. Always review reports before relying on them.

## What it demonstrates

- Multi-agent workflow with LangGraph `StateGraph` when LangGraph is installed.
- Parallel research roles: evidence scout, counterpoint analyst, and context researcher.
- Bounded follow-up research when the critic detects insufficient source coverage.
- Source validation, URL normalization, duplicate removal, and domain-diversity metrics.
- Evidence ledger with stable source IDs (`S1`, `S2`, ...).
- Report generation with inline citations and a references section.
- Deterministic mock mode for CI; optional Tavily search and OpenAI report synthesis.
- FastAPI endpoints, persisted run history, simple dashboard, CLI, Docker, and GitHub Actions.

## Architecture

```text
User research brief
        |
        v
  Planner Agent
        |
        +--------------------+--------------------+
        v                    v                    v
 Evidence Scout      Counterpoint Analyst   Context Researcher
        |                    |                    |
        +--------------------+--------------------+
                             v
                     Evidence Verifier
                             v
                       Critic Agent
                      /            \
       bounded follow-up             \
              |                        v
       Follow-up Research         Report Writer
              |                        ^
              v                        |
       Evidence Verifier --------------+
                                       v
                            Cited Research Report
```

## Quick start

Python 3.11+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open the dashboard at [http://127.0.0.1:8000](http://127.0.0.1:8000) and API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

By default, the project uses the deterministic demo search and writer. This requires no API keys.

## Enable live web search and LLM synthesis

```bash
python -m pip install -e ".[search,openai,dev]"
cp .env.example .env
```

Set the following in `.env`:

```env
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=your_tavily_api_key
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
```

The Tavily adapter gathers search result titles, URLs, snippets, and scores. The OpenAI writer receives only the retrieved evidence records and is instructed not to create unsupported citations. The final report still requires human review.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/research` | Start a research run |
| `GET` | `/api/research` | List recent research runs |
| `GET` | `/api/research/{run_id}` | Get report and evidence ledger |
| `GET` | `/api/research/{run_id}/markdown` | Download report as Markdown |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"topic":"Enterprise adoption of RAG systems","audience":"Technology leadership","focus_questions":["What are common production architectures?","How are retrieval quality and cost measured?"]}'
```

## CLI

```bash
research-report --topic "Enterprise RAG adoption" --audience "Technology leadership"
```

## Run tests

```bash
pytest
```

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

## Evidence and citation policy

- Each accepted source receives an evidence ID such as `[S1]`.
- The report references those IDs and includes the exact source URLs in References.
- The verifier removes duplicate URLs and invalid/incomplete records.
- The critic flags low source counts, low domain diversity, and absent focus-question coverage.
- Follow-up research is bounded to one round to avoid runaway agent loops.
- A source being syntactically valid or independently hosted does not make its claims true. Domain diversity is a research-quality signal, not proof of corroboration.
- Demo fixture sources are synthetic and are explicitly labeled as such.

## Security and production considerations

- Treat retrieved web content as untrusted data, never as system instructions.
- Do not expose provider API keys to the browser.
- Add user authentication, rate limits, per-user quotas, retention controls, and request-size limits before public deployment.
- Consider domain allowlists/blocklists and safe URL rendering for regulated research.
- Persist immutable source snapshots if reproducibility is required. Search indexes and snippets can change.
- Add a human review step before reports are used for legal, medical, financial, or other high-stakes decisions.

## Project layout

```text
app/
  api/routes.py
  core/config.py
  models/schemas.py
  providers/search.py
  providers/writer.py
  services/graph.py
  services/research.py
  services/repository.py
  static/
tests/
examples/
.github/workflows/ci.yml
```

## Roadmap

- [ ] Add user accounts and workspace-level collaboration.
- [ ] Add source snapshots and document attachments.
- [ ] Add claim-level evidence mapping and contradiction extraction.
- [ ] Add domain reputation policies configurable per workspace.
- [ ] Add asynchronous runs, cancellation, and progress streaming.
- [ ] Add evaluation datasets for citation precision and factual coverage.
- [ ] Add export to PDF/DOCX and scheduled research.

## License

MIT. See [LICENSE](LICENSE).
