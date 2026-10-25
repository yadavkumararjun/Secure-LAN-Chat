from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware that injects defense-in-depth HTTP security headers
    directly into response start messages without wrapping or buffering
    the request body stream. This avoids AnyIO stream errors and connection
    drops during large multipart file uploads over LAN.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["X-XSS-Protection"] = "1; mode=block"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' data: https://fonts.gstatic.com; "
                    "img-src 'self' data: blob:; "
                    "connect-src 'self' ws: wss:; "
                    "object-src 'none'; "
                    "frame-ancestors 'none';"
                )
            await send(message)

        await self.app(scope, receive, send_with_headers)
