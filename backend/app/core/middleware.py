import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class TraceAndSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        start_time = time.time()
        response: Response = await call_next(request)
        process_time = time.time() - start_time

        # Security Headers
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
