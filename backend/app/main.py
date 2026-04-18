from app.api.routes.ingestion import router as ingestion_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.projects import router as projects_router
from app.api.routes.simulations import router as simulations_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(simulations_router, prefix=settings.api_prefix)
app.include_router(ingestion_router, prefix=settings.api_prefix)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}

