import argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# Maintain standard OWASP recommended Argon2id parameters
_hasher = PasswordHasher(
    time_cost=2,        # Iterations
    memory_cost=19456,  # 19 MiB RAM cost
    parallelism=1,      # Threads
    hash_len=32,
    salt_len=16,
    type=argon2.Type.ID,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id with cryptographically random salt."""
    if not password:
        raise ValueError("Password cannot be empty")
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if the hash requires updating to newer cost parameters."""
    try:
        return _hasher.check_needs_rehash(hashed_password)
    except Exception:
        return True
