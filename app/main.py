from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import accuracy, actuals, comparison, forecasts, health, summary
from app.clients.elexon_client import ElexonClient, ElexonError
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.errors import elexon_error_handler
from app.services.data_service import DataService

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = ElexonClient(httpx.AsyncClient(), settings)
    app.state.data_service = DataService(client, settings)
    yield
    await client.close()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_exception_handler(ElexonError, elexon_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(forecasts.router)
app.include_router(actuals.router)
app.include_router(comparison.router)
app.include_router(accuracy.router)
app.include_router(summary.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
