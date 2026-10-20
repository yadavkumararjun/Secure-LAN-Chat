"""
Database Cleanup Utility for Secure LAN Chat
============================================
Allows removing dummy/test accounts, deleting specific users, cleaning up test
storage files, or completely resetting the database to a clean fresh slate.

Usage:
  python clean_db.py                     # Removes all 670+ dummy test accounts, keeps 'arjun'
  python clean_db.py --keep arjun user2  # Keeps specified accounts, deletes other dummy accounts
  python clean_db.py --delete <username> # Removes one specific username
  python clean_db.py --list              # Lists all registered usernames in the database
  python clean_db.py --reset-all         # Completely wipes the database and storage, starts fresh
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.database import engine, init_db, SessionLocal
    from app.config import settings
    from app.models import (
        User,
        UserSession,
        Conversation,
        ConversationMember,
        Message,
        FileRecord,
    )
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    sys.exit(1)


# Prefixes used by the automated test suite
TEST_PREFIXES = (
    "user_",
    "alice_",
    "bob_",
    "charlie_",
    "eve_",
    "test_",
    "broad_",
    "recon_",
    "restart_",
    "session_",
    "file_",
    "origin_",
    "frame_",
    "peer_",
    "dup_",
    "login_",
    "wrong_",
    "pager_",
    "dedup_",
    "speedy_",
    "fuzzer_",
    "sender_",
    "offline_",
    "disk_err_",
    "binary_",
    "history_",
    "safe_",
    "empty_",
    "oversized_",
    "auth_",
    "query_",
    "ws_",
    "log_",
    "presence_",
    "uploader_",
    "valid_",
    "logout_",
)


def list_users():
    """List all users in the database."""
    with SessionLocal() as db:
        users = db.query(User).order_by(User.id.asc()).all()
        print(f"\nTotal users in database: {len(users)}")
        if not users:
            print("  (Database is empty)")
            return
        print("-" * 65)
        print(f"{'ID':<6} {'Username':<28} {'Display Name':<28}")
        print("-" * 65)
        for u in users:
            print(f"{u.id:<6} {u.username:<28} {(u.display_name or ''):<28}")
        print("-" * 65 + "\n")


def delete_specific_user(username: str):
    """Delete a specific user and all associated sessions, memberships, and records."""
    cleaned = username.strip().lower()
    upload_dir = settings.get_absolute_upload_dir()

    with SessionLocal() as db:
        user = db.query(User).filter(User.username == cleaned).first()
        if not user:
            print(f"\n[ERROR] User '{cleaned}' not found in database.\n")
            return

        user_id = user.id

        # 1. Delete associated uploaded files on disk & file records
        file_records = db.query(FileRecord).filter(FileRecord.uploader_id == user_id).all()
        for fr in file_records:
            disk_file = upload_dir / fr.stored_filename
            if disk_file.is_file():
                try:
                    disk_file.unlink()
                except Exception:
                    pass
            db.delete(fr)

        # 2. Delete messages sent by user
        db.query(Message).filter(Message.sender_id == user_id).delete(synchronize_session=False)

        # 3. Delete sessions
        db.query(UserSession).filter(UserSession.user_id == user_id).delete(synchronize_session=False)

        # 4. Delete conversation memberships
        db.query(ConversationMember).filter(ConversationMember.user_id == user_id).delete(synchronize_session=False)

        # 5. Delete direct conversations that have no members left
        orphan_convs = (
            db.query(Conversation)
            .filter(Conversation.type == "direct")
            .filter(~Conversation.members.any())
            .all()
        )
        for conv in orphan_convs:
            db.delete(conv)

        # 6. Delete user
        db.delete(user)
        db.commit()
        print(f"\n[SUCCESS] Successfully removed user '{cleaned}' (ID: {user_id}) from database.\n")


def clean_test_dummy_accounts(keep_usernames: list[str] = None):
    """
    Remove automated test dummy accounts.
    Preserves any usernames in keep_usernames (defaults to 'arjun').
    """
    keep_set = set(u.strip().lower() for u in (keep_usernames or []))
    upload_dir = settings.get_absolute_upload_dir()

    with SessionLocal() as db:
        users = db.query(User).all()
        to_delete = []
        for u in users:
            uname = u.username.lower()
            if uname in keep_set:
                continue

            is_test_account = any(uname.startswith(prefix) for prefix in TEST_PREFIXES)
            if is_test_account or (keep_usernames is not None and uname not in keep_set):
                to_delete.append(u)

        if not to_delete:
            print("\n[INFO] No dummy test accounts found to delete.\n")
            return

        print(f"\nFound {len(to_delete)} dummy test accounts to remove.")
        del_ids = [u.id for u in to_delete]

        # 1. Clean uploaded files on disk & file records
        test_files = db.query(FileRecord).filter(FileRecord.uploader_id.in_(del_ids)).all()
        for fr in test_files:
            disk_file = upload_dir / fr.stored_filename
            if disk_file.is_file():
                try:
                    disk_file.unlink()
                except Exception:
                    pass
            db.delete(fr)

        # 2. Clean messages sent by test accounts
        db.query(Message).filter(Message.sender_id.in_(del_ids)).delete(synchronize_session=False)

        # 3. Clean sessions and memberships
        db.query(UserSession).filter(UserSession.user_id.in_(del_ids)).delete(synchronize_session=False)
        db.query(ConversationMember).filter(ConversationMember.user_id.in_(del_ids)).delete(synchronize_session=False)

        # 4. Clean empty direct conversations
        orphan_convs = (
            db.query(Conversation)
            .filter(Conversation.type == "direct")
            .filter(~Conversation.members.any())
            .all()
        )
        for conv in orphan_convs:
            db.delete(conv)

        # 5. Delete users
        for u in to_delete:
            db.delete(u)

        db.commit()
        print(f"[SUCCESS] Removed {len(to_delete)} dummy accounts successfully.")

        remaining = db.query(User).all()
        print(f"Remaining active accounts ({len(remaining)}): {[u.username for u in remaining]}\n")


def reset_all_database():
    """Wipe all database records and storage files, then re-seed #general-lan fresh."""
    db_file = settings.get_absolute_database_path()
    wal_file = Path(str(db_file) + "-wal")
    shm_file = Path(str(db_file) + "-shm")
    upload_dir = settings.get_absolute_upload_dir()

    # Dispose existing connection pool
    engine.dispose()

    # Delete SQLite files
    for f in [db_file, wal_file, shm_file]:
        if f.is_file():
            try:
                f.unlink()
            except Exception as e:
                print(f"Notice unlinking {f.name}: {e}")

    # Clean uploaded files
    if upload_dir.is_dir():
        for item in upload_dir.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except Exception:
                    pass

    # Re-initialize fresh schemas and default broadcast channel
    init_db()
    print("\n[SUCCESS] Database completely reset to a clean fresh slate.")
    print("Default '#general-lan' broadcast channel has been seeded.")
    print("All dummy users and test files have been removed.")
    print("You can now register a fresh user account on http://localhost:8000\n")


def main():
    parser = argparse.ArgumentParser(description="Secure LAN Chat Database Cleanup Utility")
    parser.add_argument("--list", action="store_true", help="List all usernames currently in database")
    parser.add_argument("--delete", type=str, help="Delete a specific username (e.g. --delete alice)")
    parser.add_argument(
        "--keep",
        type=str,
        nargs="+",
        default=["arjun"],
        help="Usernames to keep while removing dummy test accounts (default: arjun)",
    )
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Wipe all database records and files to start completely fresh",
    )

    args = parser.parse_args()

    if args.list:
        list_users()
    elif args.delete:
        delete_specific_user(args.delete)
    elif args.reset_all:
        reset_all_database()
    else:
        clean_test_dummy_accounts(keep_usernames=args.keep)


if __name__ == "__main__":
    main()
