import os
import shutil
from datetime import datetime
from ..config import settings
from ..database import check_db_health
from ..schemas.common import HealthResponse, DatabaseHealth, StorageHealth
from .. import __version__


def get_system_health() -> HealthResponse:
    """Gather overall backend health including database connectivity and storage status."""
    # Check Database
    db_info = check_db_health()
    db_health = DatabaseHealth(
        status=db_info.get("status", "unknown"),
        dialect=db_info.get("dialect"),
        file=db_info.get("file"),
        tables=db_info.get("tables"),
        error=db_info.get("error"),
    )

    # Check Storage Sandbox
    upload_dir = settings.get_absolute_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    exists = upload_dir.exists()
    is_writable = os.access(upload_dir, os.W_OK)

    free_mb = None
    try:
        total, used, free = shutil.disk_usage(upload_dir)
        free_mb = round(free / (1024 * 1024), 2)
    except Exception:
        pass

    storage_status = "healthy" if (exists and is_writable) else "unhealthy"
    storage_health = StorageHealth(
        status=storage_status,
        upload_dir=str(upload_dir),
        exists=exists,
        is_writable=is_writable,
        free_space_mb=free_mb,
    )

    overall_status = "healthy" if (db_health.status == "healthy" and storage_health.status == "healthy") else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        app_env=settings.APP_ENV,
        version=__version__,
        timestamp=datetime.utcnow(),
        database=db_health,
        storage=storage_health,
    )
