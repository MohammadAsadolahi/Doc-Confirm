import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import projects, documents, verification, quiz, reports

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="GenDoc Confirm",
    description="AI-Generated Document Verification & Comprehension Assurance",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(verification.router, prefix="/api", tags=["verification"])
app.include_router(quiz.router, prefix="/api", tags=["quiz"])
app.include_router(reports.router, prefix="/api", tags=["reports"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
