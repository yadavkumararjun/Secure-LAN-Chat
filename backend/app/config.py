from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Secure LAN Chat Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Network Binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Paths (defaults resolve relative to backend directory)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_URL: str = "sqlite:///./storage/data.db"
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 52428800  # 50 MB

    # Authentication & Session Settings
    SESSION_EXPIRE_HOURS: int = 24
    COOKIE_SECURE: bool = False  # Set to True only when deploying with HTTPS/TLS on LAN
    COOKIE_NAME: str = "session_id"
    MAX_SESSIONS_PER_USER: int = 5

    # Rate Limiting & Connection Hardening Defaults
    RATE_LIMIT_AUTH_ATTEMPTS: int = 10
    RATE_LIMIT_AUTH_WINDOW_SECONDS: float = 60.0
    RATE_LIMIT_CHAT_MESSAGES: int = 10
    RATE_LIMIT_CHAT_WINDOW_SECONDS: float = 3.0
    RATE_LIMIT_UPLOAD_FILES: int = 15
    RATE_LIMIT_UPLOAD_WINDOW_SECONDS: float = 60.0
    MAX_CONNECTIONS_PER_USER: int = 10
    MAX_TOTAL_CONNECTIONS: int = 500
    MAX_WS_FRAME_SIZE_BYTES: int = 65536  # 64 KB

    FRONTEND_DIST_DIR: str = "../frontend/dist"

    # Explicit CORS Origins for development
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"

    # Regex pattern to securely allow local network IP addresses without wildcard "*"
    # Matches private IPv4 addresses: 127.0.0.1, 10.x.x.x, 192.168.x.x, 172.16-31.x.x on any port (HTTP or HTTPS)
    CORS_ORIGIN_REGEX: str = (
        r"^https?:\/\/(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
    )

    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def get_absolute_upload_dir(self) -> Path:
        """Resolve upload directory as an absolute Path outside static public folders."""
        upload_path = Path(self.UPLOAD_DIR)
        if not upload_path.is_absolute():
            upload_path = (self.BASE_DIR / upload_path).resolve()
        return upload_path

    def get_absolute_database_path(self) -> Path:
        """Extract and resolve SQLite database file path."""
        if self.DATABASE_URL.startswith("sqlite:///"):
            raw_path = self.DATABASE_URL.replace("sqlite:///", "")
            db_path = Path(raw_path)
            if not db_path.is_absolute():
                db_path = (self.BASE_DIR / db_path).resolve()
            return db_path
        return Path(self.DATABASE_URL)

    def get_absolute_frontend_dist(self) -> Path:
        """Resolve frontend dist directory as an absolute Path."""
        dist_path = Path(self.FRONTEND_DIST_DIR)
        if not dist_path.is_absolute():
            dist_path = (self.BASE_DIR / dist_path).resolve()
        return dist_path

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
