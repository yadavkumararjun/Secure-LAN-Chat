from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .logging_config import setup_logging, logger
from .database import init_db
from .errors import register_exception_handlers
from .middleware import SecurityHeadersMiddleware
from .routers import health_router, auth_router, users_router, chat_router, files_router
from .websocket import ws_router
from . import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and graceful shutdown."""
    # Startup sequence
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{__version__} [{settings.APP_ENV}]")

    # 1. Initialize SQLite Database & Tables
    init_db()

    # 2. Ensure Sandboxed Uploads Directory Exists (outside public static)
    upload_dir = settings.get_absolute_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Sandboxed uploads directory ready at: {upload_dir}")

    yield

    # Shutdown sequence
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="Backend API and WebSocket engine for Secure LAN Chat and File Sharing.",
        lifespan=lifespan,
    )

    # Configure CORS: Explicit development origins + LAN Subnet Regex (No wildcard '*' with credentials)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=settings.CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-File-Checksum-SHA256"],
    )

    # Attach defense-in-depth HTTP security headers (nosniff, DENY, CSP)
    app.add_middleware(SecurityHeadersMiddleware)

    # Register centralized exception handlers
    register_exception_handlers(app)

    # Include Routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(chat_router)
    app.include_router(files_router)
    app.include_router(ws_router)

    # Resolve production frontend directory (Single-Origin LAN Deployment)
    frontend_dist = settings.get_absolute_frontend_dist()
    dist_assets = frontend_dist / "assets"
    if dist_assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(dist_assets)), name="assets")

    @app.get("/", tags=["Root"])
    async def root(request: Request):
        accept = request.headers.get("accept", "")
        index_file = frontend_dist / "index.html"
        # Serve frontend SPA if client requests HTML and compiled index.html exists
        if "text/html" in accept and index_file.is_file():
            return FileResponse(index_file)
        return {
            "message": "Secure LAN Chat API is operational",
            "version": __version__,
            "health_check": "/api/health",
            "docs": "/docs",
        }

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str, request: Request):
        # Do not catch API, WS, docs, or OpenAPI endpoints
        if (
            full_path.startswith("api/")
            or full_path.startswith("ws/")
            or full_path in ("docs", "redoc", "openapi.json")
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Endpoint /{full_path} not found")

        # Check if requested static file exists in frontend dist (e.g., favicon or assets)
        static_file = frontend_dist / full_path
        if static_file.is_file() and static_file.resolve().is_relative_to(frontend_dist):
            return FileResponse(static_file)

        # Fallback to SPA index.html for client-side navigation
        index_file = frontend_dist / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    return app


app = create_app()
