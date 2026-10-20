import pytest
from sqlalchemy import text
from app.database import engine, init_db, check_db_health, SessionLocal
from app.models import User, Conversation, ConversationMember, Message, FileRecord


def test_database_initialization():
    """Verify that init_db creates all required SQLite tables."""
    init_db()

    with engine.connect() as conn:
        tables = engine.dialect.get_table_names(conn)

    expected_tables = {
        "users",
        "conversations",
        "conversation_members",
        "messages",
        "file_records",
    }

    assert expected_tables.issubset(set(tables)), f"Missing tables: {expected_tables - set(tables)}"


def test_sqlite_pragmas():
    """Verify that SQLite WAL mode and foreign key enforcement are configured."""
    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode;")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys;")).scalar()

    assert str(journal_mode).lower() == "wal", f"Expected WAL mode, got {journal_mode}"
    assert foreign_keys == 1, "Expected foreign keys to be enabled (1)"


def test_database_health_check():
    """Verify check_db_health probe returns healthy status."""
    health = check_db_health()
    assert health["status"] == "healthy"
    assert health["dialect"] == "sqlite"
    assert isinstance(health["tables"], list)
    assert len(health["tables"]) >= 5


def test_model_crud_and_relationships():
    """Verify basic model insertion and relationship linking."""
    init_db()
    db = SessionLocal()

    import uuid
    try:
        # Create test user
        test_user = User(
            username=f"test_peer_{uuid.uuid4().hex[:8]}",
            display_name="Test Peer",
            avatar="TP",
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        assert test_user.id is not None

        # Create test conversation
        test_conv = Conversation(
            id=f"test-channel-{uuid.uuid4().hex[:8]}",
            type="broadcast",
            name="#test-channel",
        )
        db.add(test_conv)
        db.commit()

        # Add member
        member = ConversationMember(
            conversation_id=test_conv.id,
            user_id=test_user.id,
            role="admin",
        )
        db.add(member)
        db.commit()

        # Add message
        msg = Message(
            conversation_id=test_conv.id,
            sender_id=test_user.id,
            content="Hello LAN database test",
            message_type="text",
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        assert msg.id is not None
        assert msg.conversation.name == "#test-channel"
        assert msg.sender.username == test_user.username

    finally:
        db.close()
