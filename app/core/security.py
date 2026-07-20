import hashlib
import hmac
import secrets

from passlib.context import CryptContext

from app.core.config import settings

# bcrypt - same algorithm Laravel's Hash::make() uses by default, so existing
# password hashes from the Laravel users table keep working unchanged.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


def generate_otp() -> str:
    """6-digit numeric OTP, same shape as Laravel's mt_rand(100000, 999999)."""
    return str(secrets.randbelow(900000) + 100000)


def generate_login_token() -> str:
    """
    Opaque one-time token handed back from /auth/login while the user is
    mid-OTP-flow (not an access token yet - just correlates login -> check-otp).
    """
    return secrets.token_urlsafe(32)


def generate_plain_access_token() -> str:
    """The raw bearer token given to the client exactly once (like Sanctum's plainTextToken)."""
    return secrets.token_urlsafe(40)


def hash_access_token(plain_token: str) -> str:
    """
    We only ever store this hash, never the plain token - if the DB leaks,
    tokens can't be replayed. Verification re-hashes the incoming token and
    compares in constant time.
    """
    return hmac.new(
        settings.TOKEN_SECRET.encode(), plain_token.encode(), hashlib.sha256
    ).hexdigest()
