"""FastAPI application for the ElectricalTwin advisory API.

Every endpoint is read-only. At startup the application configures structured
JSON logging and runs :func:`assert_safe_startup`, which fails closed if any
safety invariant is not satisfied.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, assert_safe_startup, load_settings
from app.logging_config import configure_logging
from packages.canonical_electrical_model.provenance import provenance_vocabulary
from packages.canonical_electrical_model.safety import control_boundary
from packages.s3m_engine_contract.grounding import GROUNDING_RULE_DEFINITIONS
from packages.s3m_engine_contract.packets import (
    EngineClass,
    PacketClass,
    UrgencyLevel,
)
from packages.s3m_engine_contract.routing import routing_table_as_dicts

logger = logging.getLogger("electricaltwin.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = load_settings()
    configure_logging(settings.log_level)
    assert_safe_startup(settings)
    app.state.settings = settings
    logger.info(
        "startup complete",
        extra={
            "deployment_profile": settings.deployment_profile.value,
            "service_name": settings.service_name,
            "posture": "advisory-read-only",
        },
    )
    yield
    logger.info("shutdown complete")


def create_app() -> FastAPI:
    """Application factory for the ElectricalTwin advisory API."""

    app = FastAPI(
        title="S3M ElectricalTwin Advisory API",
        version="0.0.0",
        summary="Advisory, read-only electrical reasoning platform (Work Package 0).",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, object]:
        settings: Settings = getattr(app.state, "settings", load_settings())
        return {
            "status": "ok",
            "service": settings.service_name,
            "deployment_profile": settings.deployment_profile.value,
            "posture": "advisory-read-only",
        }

    @app.get("/safety", tags=["safety"])
    def safety() -> dict[str, object]:
        boundary = control_boundary()
        return {
            "control_write_enabled": boundary.control_write_enabled,
            "posture": boundary.posture,
            "advisory_statement": boundary.advisory_statement,
            "prohibited_actions": list(boundary.prohibited_actions),
            "permitted_actions": list(boundary.permitted_actions),
        }

    @app.get("/meta/provenance", tags=["meta"])
    def meta_provenance() -> dict[str, dict[str, str]]:
        return provenance_vocabulary()

    @app.get("/engine/contract", tags=["engine"])
    def engine_contract() -> dict[str, object]:
        return {
            "engine_classes": [engine.value for engine in EngineClass],
            "packet_classes": [packet.value for packet in PacketClass],
            "urgency_levels": [level.value for level in UrgencyLevel],
            "routing_table": routing_table_as_dicts(),
        }

    @app.get("/engine/grounding-rules", tags=["engine"])
    def engine_grounding_rules() -> dict[str, object]:
        return {
            "rules": [
                {"code": code, "definition": definition}
                for code, definition in GROUNDING_RULE_DEFINITIONS.items()
            ]
        }

    return app


app = create_app()
