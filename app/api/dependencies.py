"""
API dependencies for dependency injection.
Provides database sessions, current user, etc.
"""
from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.
    Ensures session is closed after request.
    """
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


# TODO: Add authentication dependencies when implementing auth
# def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
#     """Get current authenticated user from JWT token"""
#     pass
