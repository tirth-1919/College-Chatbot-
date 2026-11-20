"""AI FAQ College Chat Bot - FastAPI Application Entry Point.

Configures application lifecycle, CORS, security headers, correlation IDs,
tenant middleware, API routers, Sentry monitoring, and OpenAPI documentation.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import logger
from app.core.sentry import init_sentry
from app.middleware.access_log_middleware import AccessLogMiddleware
from app.middleware.security_middleware import (
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
)
from app.middleware.tenant_middleware import TenantMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Starting %s in %s environment...", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # Initialize Sentry error telemetry if configured
    init_sentry()

    logger.info("OpenAPI Documentation available at: /docs")
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-Tenant AI-Powered College FAQ & Knowledge Grounding SaaS Platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 1. Live HTTP Access Log (outermost — captures full round-trip time)
app.add_middleware(AccessLogMiddleware)

# 2. Request Correlation ID & Performance Tracing Middleware
app.add_middleware(CorrelationIdMiddleware)

# 3. HTTP Security Headers (OWASP Clickjacking, MIME-sniffing, XSS, HSTS)
app.add_middleware(SecurityHeadersMiddleware)

# 4. Request Body Size Limit Defense (DoS prevention)
app.add_middleware(RequestSizeLimitMiddleware)

# 5. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
)

# 6. Tenant Scoping Middleware
app.add_middleware(TenantMiddleware)

# 7. Register API Version 1 Routers
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


# Root Endpoint
@app.get("/", tags=["Root"])
async def root():
    """Welcomes visitors and provides links to health and API documentation."""
    return {
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs",
        "health_check": f"{settings.API_V1_PREFIX}/health",
        "readiness_check": f"{settings.API_V1_PREFIX}/health/ready",
        "version": "1.0.0",
    }


# Global Exception Handler (Never exposes internal stack traces or secrets)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unhandled exceptions and returns a consistent JSON envelope with correlation ID."""
    req_id = getattr(request.state, "correlation_id", "unknown")
    origin = request.headers.get("origin")
    cors_headers = {}
    if origin in settings.BACKEND_CORS_ORIGINS:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    logger.error(
        "Unhandled Exception on %s [RequestID: %s]: %s",
        request.url.path,
        req_id,
        str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please contact college support quoting this Request ID.",
            "request_id": req_id,
        },
        headers=cors_headers,
    )
