from fastapi import APIRouter, status
from ..schemas.common import HealthResponse
from ..services.health_service import get_system_health

router = APIRouter(prefix="/api", tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Backend Health & Subsystem Status",
    description="Returns current server status, SQLite database connectivity, and upload storage health.",
)
async def check_health() -> HealthResponse:
    """Check backend, database, and storage system health."""
    return get_system_health()
