from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.api import api_router
from app.api.v1.endpoints import health
from app.services.embedding_service import EmbeddingUnavailableError
import uuid
import logging

from app.core.logging import setup_logging, correlation_id_var

# Initialize structured logging
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lenny Growth Assistant API",
    version="1.0.0",
    openapi_url="/openapi.json"
)


# Correlation-ID middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    # Set for structured logging
    token = correlation_id_var.set(correlation_id)
    
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        correlation_id_var.reset(token)


# Global exception handler: EmbeddingUnavailableError → 503
@app.exception_handler(EmbeddingUnavailableError)
async def embedding_unavailable_handler(request: Request, exc: EmbeddingUnavailableError):
    logger.error(f"Embedding service unavailable: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": f"Embedding service unavailable: {str(exc)}"},
    )


# Set all CORS enabled origins
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(api_router, prefix="/api/v1")
