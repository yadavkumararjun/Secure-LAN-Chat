"""Security and cryptography utilities placeholder for Phase 3."""
import secrets


def generate_session_token() -> str:
    """Generate a cryptographically secure random session token."""
    return secrets.token_urlsafe(32)
