import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Multi-Agent Research & Report Generator")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_path: str = os.getenv("DATABASE_PATH", "./research_runs.sqlite3")
    search_provider: str = os.getenv("SEARCH_PROVIDER", "demo").lower()
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "demo").lower()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    min_source_domains: int = int(os.getenv("MIN_SOURCE_DOMAINS", "2"))

    def ensure_database_parent(self) -> None:
        path = Path(self.database_path)
        if str(path.parent) not in ("", "."):
            path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
