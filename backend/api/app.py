"""UNMAPPED FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import close_tavily_client, get_skill_matcher, get_tavily_client
from api.routes import analyze, countries, policymaker, signals, skills
from config.country_loader import list_country_codes
from config.settings import get_settings
from core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log = get_logger("api")
    settings = get_settings()
    settings.ensure_dirs()
    matcher = get_skill_matcher()
    tavily = get_tavily_client()
    log.info(
        "api.startup",
        countries=list_country_codes(),
        skills_loaded=len(matcher.taxonomy.get("skills", [])),
        cache_ttl_hours=settings.cache_ttl_hours,
        embeddings_enabled=settings.enable_embeddings,
        tavily_enabled=tavily.is_enabled(),
    )
    yield
    await close_tavily_client()
    log.info("api.shutdown")


app = FastAPI(
    title="UNMAPPED API",
    description=(
        "Skills-to-Opportunity infrastructure for the World Bank Youth Summit Hackathon. "
        "Country-agnostic, ESCO/ISCO-grounded, with full source provenance on every value."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(countries.router)
app.include_router(skills.router)
app.include_router(signals.router)
app.include_router(policymaker.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "UNMAPPED API",
        "version": "1.0.0",
        "docs": "/docs",
        "available_countries": list_country_codes(),
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "healthy"}
