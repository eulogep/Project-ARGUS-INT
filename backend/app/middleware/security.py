# ==============================================================================
# Project ARGUS-INT - Security & Zero Trust Middleware
# ==============================================================================

import time
import logging
from fastapi import Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
import redis

logger = logging.getLogger(__name__)

# Redis rate limiting client
try:
    r_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
except Exception as e:
    logger.warning(f"[Security] Failed to connect to Redis for rate-limiting, falling back to in-memory: {e}")
    r_client = None

_in_memory_limits = {}

def check_rate_limit(ip: str, limit: int = 100, window: int = 60) -> bool:
    """
    Checks rate limit for an IP address. Default: 100 req/min.
    """
    now = int(time.time())
    bucket_time = now // window
    key = f"rate:{ip}:{bucket_time}"
    
    if r_client:
        try:
            current = r_client.get(key)
            if current and int(current) >= limit:
                return True
            pipe = r_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window * 2) # keep alive a bit longer for safety
            pipe.execute()
            return False
        except Exception as e:
            logger.debug(f"[Security] Redis rate limit error: {e}")
            pass
            
    # In-memory fallback
    bucket = _in_memory_limits.get(key, 0)
    if bucket >= limit:
        return True
    _in_memory_limits[key] = bucket + 1
    
    # Simple clean up of old keys
    if len(_in_memory_limits) > 5000:
        _in_memory_limits.clear()
        
    return False

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Rate limiting check
        client_ip = request.client.host if request.client else "127.0.0.1"
        
        # Whitelist localhost for ease of development/testing, but rate limit others
        if client_ip not in ("127.0.0.1", "localhost") and check_rate_limit(client_ip):
            logger.warning(f"[Security] Rate limit exceeded for client: {client_ip}")
            return Response(content='{"detail": "Too Many Requests"}', status_code=429, media_type="application/json")
        
        # 2. Proceed with request
        response = await call_next(request)
        
        # 3. Inject Security Headers
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "connect-src 'self' ws: wss:; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

def setup_security_middleware(app):
    """Registers security middlewares on FastAPI application."""
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Configure CORS restriction to frontend host
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info("[Security] Zero Trust headers and middleware configured.")
