from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.security.rate_limit import limiter
from app.routers import auth, students, profiles, universities, documents, sop, interview, admin, visa, applications


def create_app() -> FastAPI:
    app = FastAPI(
        title="StudyAI Platform",
        version="1.0.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins.split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Prometheus metrics — exposed at /api/metrics
    Instrumentator().instrument(app).expose(app, endpoint="/api/metrics", include_in_schema=False)


    # Routers
    app.include_router(auth.router,         prefix="/api/auth",         tags=["auth"])
    app.include_router(students.router,     prefix="/api/students",     tags=["students"])
    app.include_router(profiles.router,     prefix="/api/profile",      tags=["profile"])
    app.include_router(universities.router, prefix="/api/universities",  tags=["universities"])
    app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
    app.include_router(documents.router,    prefix="/api/documents",    tags=["documents"])
    app.include_router(sop.router,          prefix="/api/sop",          tags=["sop"])
    app.include_router(interview.router,    prefix="/api/interview",    tags=["interview"])
    app.include_router(visa.router,         prefix="/api/visa",         tags=["visa"])
    app.include_router(admin.router,        prefix="/api/admin",        tags=["admin"])

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
