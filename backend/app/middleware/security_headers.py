from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi import Request, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that injects defense-in-depth HTTP security headers into all responses:
    - Mitigates Clickjacking (X-Frame-Options: DENY)
    - Mitigates MIME Confusion / Sniffing (X-Content-Type-Options: nosniff)
    - Enforces Content Security Policy (CSP)
    - Restricts Referrer leakage
    - Enforces Permissions Policy
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 1. Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Legacy XSS filter activation
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Strict referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Restrict capabilities
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # 6. Content Security Policy for LAN web clients
        # Allows self assets, inline CSS styles, data/blob images, self API and WebSockets
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        return response
