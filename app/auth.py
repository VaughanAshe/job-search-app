"""Authentication: password hashing, session management, route dependencies."""

from datetime import datetime, timedelta
from typing import Optional
import secrets

import bcrypt
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse

from app.db import get_db, User

SESSION_COOKIE = "jobsearch_session"
SESSION_EXPIRY_HOURS = 72


def hash_password(password: str) -> str:
    """Hash a password using bcrypt directly."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_session(request: Request, user: User):
    """Set a session cookie. Token = user_id + random nonce."""
    token = f"{user.id}:{secrets.token_urlsafe(32)}"
    request.session["user_id"] = user.id
    request.session["token"] = token


def clear_session(request: Request):
    request.session.clear()


def get_current_user(request: Request, db=Depends(get_db)) -> Optional[User]:
    """Dependency: returns the logged-in user or raises 401."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        clear_session(request)
        return None
    return user


def require_user(request: Request, db=Depends(get_db)) -> User:
    """Dependency: requires login, redirects to /login if not authenticated."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def require_admin(request: Request, db=Depends(get_db)) -> User:
    """Dependency: requires admin login."""
    user = require_user(request, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
