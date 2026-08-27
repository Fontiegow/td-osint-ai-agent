import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import OSINTBaseException
from app.core.logging import setup_logging
from app.infrastructure.database import async_engine
from app.infrastructure.qdrant import qdrant_manager
from app.infrastructure.redis import redis_client

setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup_initiated", environment=settings.ENVIRONMENT)
    await redis_client.connect()
    await qdrant_manager.connect()
    logger.info("infrastructure_connections_established")
    yield
    logger.info("application_shutdown_initiated")
    await redis_client.close()
    await qdrant_manager.close()
    await async_engine.dispose()
    logger.info("infrastructure_connections_closed")


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def request_correlation_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(OSINTBaseException)
async def osint_exception_handler(request: Request, exc: OSINTBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": structlog.contextvars.get_contextvars().get("request_id"),
            }
        },
    )


@app.get("/api/v1/health/live", tags=["Health"])
async def liveness_check():
    return {"status": "alive"}


@app.get("/api/v1/health/ready", tags=["Health"])
async def readiness_check():
    health_status = {"database": False, "redis": False, "qdrant": False}

    # Check Postgres
    try:
        async with async_engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        health_status["database"] = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness_check_failed", dependency="database", error=str(exc))

    # Check Redis
    try:
        health_status["redis"] = await redis_client.ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness_check_failed", dependency="redis", error=str(exc))

    # Check Qdrant
    try:
        health_status["qdrant"] = await qdrant_manager.ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness_check_failed", dependency="qdrant", error=str(exc))

    is_healthy = all(health_status.values())
    status_code = (
        status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_healthy else "unhealthy",
            "dependencies": health_status,
        },
    )