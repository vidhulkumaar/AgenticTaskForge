from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings
import httpx

router = APIRouter()

@router.get("/live", status_code=status.HTTP_200_OK)
def health_live():
    return {"status": "ok"}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def health_ready(db: AsyncSession = Depends(get_db)):
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # Ollama check
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                checks["ollama"] = "ok"
            else:
                checks["ollama"] = f"unhealthy (HTTP {resp.status_code})"
    except Exception:
        checks["ollama"] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())
    if not all_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "checks": checks}
        )

    return {"status": "ok", "checks": checks}

