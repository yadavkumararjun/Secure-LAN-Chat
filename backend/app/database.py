import sqlite3
from typing import Dict, Any, Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import NullPool
from .config import settings
from .logging_config import logger

# Ensure database directory exists before binding SQLite
db_path = settings.get_absolute_database_path()
db_path.parent.mkdir(parents=True, exist_ok=True)

# Build engine (check_same_thread=False allows FastAPI multi-threaded requests; NullPool avoids SQLite connection pool limits)
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    f"sqlite:///{db_path.as_posix()}" if "sqlite" in settings.DATABASE_URL else settings.DATABASE_URL,
    connect_args=connect_args,
    poolclass=NullPool,
)


# SQLite PRAGMAs for high-performance LAN concurrency & integrity
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schemas, apply lightweight migrations, and seed default channels."""
    # Ensure models are imported so Base.metadata knows about them
    from . import models  # noqa: F401
    from sqlalchemy import inspect

    logger.info(f"Initializing database schemas at: {db_path}")
    Base.metadata.create_all(bind=engine)

    # Lightweight migrations
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if "messages" in tables:
                existing_cols = [c["name"] for c in inspector.get_columns("messages")]
                if "client_msg_id" not in existing_cols:
                    logger.info("Migrating table 'messages': adding column 'client_msg_id'")
                    conn.execute(text("ALTER TABLE messages ADD COLUMN client_msg_id VARCHAR(64);"))
                    conn.commit()

            if "file_records" in tables:
                file_cols = [c["name"] for c in inspector.get_columns("file_records")]
                if "conversation_id" not in file_cols:
                    logger.info("Migrating table 'file_records': adding column 'conversation_id'")
                    conn.execute(text("ALTER TABLE file_records ADD COLUMN conversation_id VARCHAR(36);"))
                    conn.commit()
    except Exception as e:
        logger.warning(f"Column migration check notice: {e}")

    # Seed global broadcast channel
    try:
        from .models import Conversation, Message
        with SessionLocal() as session:
            broadcast = session.query(Conversation).filter(Conversation.id == "broadcast-general").first()
            if not broadcast:
                logger.info("Seeding default '#general-lan' broadcast channel")
                broadcast = Conversation(
                    id="broadcast-general",
                    type="broadcast",
                    name="#general-lan",
                )
                session.add(broadcast)
                session.commit()

                # Add initial system notice if no messages
                msg = Message(
                    conversation_id="broadcast-general",
                    sender_id=None,
                    content="Welcome to Secure LAN Chat! Messages in #general-lan are broadcast to all connected peers on the local network.",
                    message_type="system",
                )
                session.add(msg)
                session.commit()
    except Exception as e:
        logger.error(f"Error seeding broadcast channel: {e}")

    logger.info("Database schema initialization complete.")


_cached_tables = None

def check_db_health() -> Dict[str, Any]:
    """Execute a lightweight probe to verify database connectivity."""
    global _cached_tables
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            if _cached_tables is None:
                _cached_tables = engine.dialect.get_table_names(conn)
        return {
            "status": "healthy",
            "dialect": "sqlite",
            "file": str(db_path),
            "tables": _cached_tables or [],
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
