"""
API dependencies for dependency injection.
Provides database sessions, current user, authentication, RBAC.
"""
from typing import Generator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


# OAuth2 scheme for extracting token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.
    Ensures session is closed after request.

    Usage:
        @router.get("/")
        async def endpoint(db: Session = Depends(get_db_session)):
            ...
    """
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    AUTHENTICATION FLOW:
    1. Extract token from Authorization: Bearer <token> header
    2. Verify token signature and expiration
    3. Extract username from token payload
    4. Fetch user from database
    5. Return user object

    WHY this approach:
    - Stateless: No server-side session storage
    - Scalable: Any server can verify token
    - Fast: No session lookup, just crypto verification
    - Secure: Token signed with secret key

    Usage:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            # current_user is authenticated User object
            return {"user": current_user.username}

    Args:
        token: JWT token from Authorization header (automatic via oauth2_scheme)
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException 401: Invalid, expired, or missing token
        HTTPException 404: User not found in database (token valid but user deleted)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify and decode token
        payload = AuthService.verify_token(token)
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    # Fetch user from database
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user is still active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control (RBAC).

    RBAC HIERARCHY:
    - affiliate: Lowest privilege (can only view own prospects)
    - broker: Can manage prospects, quotes, policies
    - manager: Can view team data, approve commissions
    - head_of_sales: Can view all data, generate reports
    - admin: Full access to everything

    WHY role-based access:
    - Security: Prevent unauthorized actions
    - Compliance: Audit who can do what
    - Business logic: Different users have different permissions
    - Multi-tenancy: Brokers only see their data

    Usage:
        # Only admins can access
        @router.post("/users")
        async def create_user(
            user_data: UserCreate,
            current_user: User = Depends(require_role([UserRole.ADMIN]))
        ):
            ...

        # Brokers and managers can access
        @router.get("/prospects")
        async def list_prospects(
            current_user: User = Depends(require_role([UserRole.BROKER, UserRole.MANAGER]))
        ):
            ...

    Args:
        allowed_roles: List of roles that can access the endpoint

    Returns:
        Dependency function that checks user role

    Raises:
        HTTPException 403: User role not in allowed_roles
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """
        Check if current user's role is in allowed roles.

        Args:
            current_user: Authenticated user from get_current_user

        Returns:
            User object if authorized

        Raises:
            HTTPException 403: Insufficient permissions
        """
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker


def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure user is active.

    This is redundant with get_current_user (which already checks is_active),
    but useful for explicit clarity in endpoint signatures.

    Usage:
        @router.get("/dashboard")
        async def dashboard(user: User = Depends(require_active_user)):
            # user is guaranteed to be active
            ...

    Args:
        current_user: Authenticated user

    Returns:
        User object if active

    Raises:
        HTTPException 403: User is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user
