# ==============================================================================
# Project ARGUS-INT - Security & Zero Trust Middleware
# ==============================================================================
"""
Security middleware for ARGUS-INT FastAPI backend.
Implements Zero Trust principles: rate limiting, CSP headers, CORS, structured logging.
"""

import os
import re
import time
import uuid
from typing import Callable, Awaitable

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from app.observability.logging import logger

# Configuration from environment (with secure defaults)
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "1000"))
CSP_REPORT_URI = os.getenv("CSP_REPORT_URI", "")  # Empty = no reporting endpoint
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
ENABLE_CORS = os.getenv("ENABLE_CORS", "false").lower() == "true"

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute", f"{RATE_LIMIT_PER_DAY}/day"],
    enabled=RATE_LIMIT_ENABLED,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://")  # Use Redis in prod: "redis://localhost:6379"
)


def setup_security_middleware(app):
    """
    Apply all security middleware to the FastAPI application.
    Should be called after app creation but before adding routers.
    """
    
    # 1. Rate limiting exception handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.state.limiter = limiter
    
    # 2. CORS middleware (only if explicitly enabled)
    if ENABLE_CORS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],  # Restrict further in production
            expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
        )
        logger.info("CORS middleware enabled", allowed_origins=ALLOWED_ORIGINS)
    else:
        logger.info("CORS middleware disabled (default for air-gapped deployments)")
    
    # 3. Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Add security-focused HTTP headers to all responses."""
        
        # Generate correlation ID for request tracing if not present
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Start timing for performance logging
        start_time = time.time()
        
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error with correlation ID before re-raising
            logger.error(
                "Request processing error",
                path=request.url.path,
                method=request.method,
                correlation_id=correlation_id,
                error=str(e),
                exc_info=True
            )
            raise
        
        # Add security headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content-Security-Policy: strict but functional for Next.js + Canvas + WebSockets
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # unsafe-inline needed for Next.js hydration
            "style-src 'self' 'unsafe-inline'",   # unsafe-inline needed for dynamic styles
            "connect-src 'self' ws: wss: http: https:",  # Allow API + WebSocket connections
            "img-src 'self' data: blob: https:",   # Allow data URLs for graph images
            "font-src 'self'",
            "frame-ancestors 'none'",  # Prevent clickjacking
            "form-action 'self'",
            "upgrade-insecure-requests",
        ]
        if CSP_REPORT_URI:
            csp_directives.append(f"report-uri {CSP_REPORT_URI}")
            csp_directives.append(f"report-to {CSP_REPORT_URI}")
        
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Add timing header for performance monitoring (optional)
        elapsed_ms = (time.time() - start_time) * 1000
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        
        # Log successful request (structured, no sensitive data)
        logger.info(
            "Request completed",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            correlation_id=correlation_id,
            user_agent=request.headers.get("user-agent", "")[:100]  # Truncate for safety
        )
        
        return response
    
    # 4. Request validation middleware (basic input sanitization)
    @app.middleware("http")
    async def validate_request_inputs(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Basic validation and sanitization of request inputs."""
        
        # Block suspicious user-agents (basic bot/scanner detection)
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_patterns = [
            r'sqlmap', r'nmap', r'masscan', r'nikto', r'dirb', r'gobuster',
            r'burp', r'owasp', r'acunetix', r'nessus'
        ]
        if any(re.search(pattern, user_agent) for pattern in suspicious_patterns):
            logger.warning(
                "Suspicious user-agent blocked",
                user_agent=user_agent[:100],
                path=request.url.path,
                ip=get_remote_address(request)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request blocked by security policy"
            )
        
        # Sanitize query parameters (prevent basic injection attempts)
        for key, values in request.query_params.multi_items():
            if isinstance(values, str):
                # Block null bytes and basic script tags
                if '\x00' in values or '<script' in values.lower():
                    logger.warning(
                        "Suspicious query parameter blocked",
                        key=key,
                        path=request.url.path,
                        ip=get_remote_address(request)
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request parameters"
                    )
        
        return await call_next(request)
    
    # 5. CSP violation reporting endpoint (if configured)
    if CSP_REPORT_URI:
        @app.post(CSP_REPORT_URI)
        async def csp_report(request: Request):
            """Endpoint for receiving CSP violation reports."""
            try:
                report = await request.json()
                logger.warning(
                    "CSP violation reported",
                    report=report,
                    user_agent=request.headers.get("user-agent", "")[:100]
                )
                # In production: forward to SIEM or monitoring system
                return {"status": "received"}
            except Exception as e:
                logger.error("Failed to process CSP report", error=str(e))
                raise HTTPException(status_code=400, detail="Invalid report format")
    
    logger.info("Security middleware initialized", rate_limit=RATE_LIMIT_ENABLED, cors=ENABLE_CORS)
