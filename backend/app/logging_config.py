import logging
import sys
from .config import settings


def setup_logging():
    """Configure application-wide structured console logging."""
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d - %(message)s"
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Silence overly verbose external loggers if in info mode
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("secure_lan_chat")
