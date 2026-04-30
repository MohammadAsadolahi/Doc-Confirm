import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.api import projects, documents, verification, quiz, reports
from app.store import list_sessions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

_start_time = time.time()

app = FastAPI(
    title="GenDoc Confirm",
    description="AI-Generated Document Verification & Comprehension Assurance",
    version="0.1.0",
)


# ─── Request-ID Middleware ───────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(verification.router, prefix="/api/v1",
                   tags=["verification"])
app.include_router(quiz.router, prefix="/api/v1", tags=["quiz"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])

# Backward-compat: keep /api/health alive


@app.get("/api/health")
@app.get("/api/v1/health")
async def health_check():
    uptime = int(time.time() - _start_time)
    llm_status = "ok" if settings.openai_api_key else "down"
    return {
        "status": "healthy",
        "version": "0.1.0",
        "checks": {
            "llm_provider": llm_status,
            "active_sessions": len(list_sessions()),
            "uptime_seconds": uptime,
        },
    }
