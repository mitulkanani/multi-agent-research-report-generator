from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routes import router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0", description="Multi-agent research workflow with an evidence ledger and cited reports.")
app.include_router(router)
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/static/{asset}", include_in_schema=False)
def static_asset(asset: str):
    safe = {"styles.css", "app.js"}
    if asset not in safe:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(STATIC_DIR / asset)
