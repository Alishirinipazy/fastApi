from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import hash_access_token
from app.db.session import get_db
from app.models import AccessToken, User

bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_token(
    credentials: HTTPAuthorizationCredentials | None, db: Session
) -> AccessToken:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Unauthenticated.")

    token_hash = hash_access_token(credentials.credentials)
    token = db.query(AccessToken).filter(AccessToken.token_hash == token_hash).first()

    if token is None:
        raise HTTPException(status_code=401, detail="Unauthenticated.")

    if token.expires_at and token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Unauthenticated.")

    token.last_used_at = datetime.utcnow()
    db.add(token)
    db.commit()

    return token


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Equivalent to Laravel's auth:sanctum middleware with ability('user')."""
    token = _resolve_token(credentials, db)
    if "user" not in token.abilities:
        raise HTTPException(status_code=403, detail="Forbidden.")
    return token.user


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Equivalent to Laravel's auth:sanctum middleware with ability('admin')."""
    token = _resolve_token(credentials, db)
    if "admin" not in token.abilities or token.user.is_admin == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    return token.user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Like get_current_user, but returns None instead of raising 401 when
    there's no (valid) token - for endpoints usable by both guests and
    logged-in users, e.g. the AI shopping assistant, which can search and
    answer questions for anyone but only add to cart for a logged-in user.
    """
    if credentials is None:
        return None
    try:
        token = _resolve_token(credentials, db)
    except HTTPException:
        return None
    if "user" not in token.abilities:
        return None
    return token.user
