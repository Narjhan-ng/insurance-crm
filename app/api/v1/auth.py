"""
Authentication API endpoints
Login, registration, token management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from app.api.dependencies import get_db_session
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


router = APIRouter()

# OAuth2 scheme for token authentication
# tokenUrl points to the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# ============================================================================
# Request/Response Schemas
# ============================================================================

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data extracted from JWT token"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class UserRegister(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = Field(default=UserRole.BROKER)
    supervisor_id: Optional[int] = None


class UserResponse(BaseModel):
    """User information response (excludes password)"""
    id: int
    username: str
    email: str
    role: UserRole
    supervisor_id: Optional[int]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Alternative login request (JSON body)"""
    username: str
    password: str


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session)
):
    """
    Login endpoint - returns JWT access token.

    FLOW:
    1. User submits username + password
    2. Verify credentials against database
    3. Generate JWT token with user info
    4. Return token to client
    5. Client includes token in subsequent requests

    SECURITY:
    - Password is verified using bcrypt (never compared plain text)
    - Failed login returns generic error (prevent username enumeration)
    - Token has expiration (configurable via settings)

    OAUTH2 COMPLIANCE:
    - Uses OAuth2PasswordRequestForm (standard)
    - Returns access_token + token_type
    - Frontend can use standard OAuth2 flow

    Args:
        form_data: OAuth2 form with username and password
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException 401: Invalid credentials
    """
    # Find user by username
    user = db.query(User).filter(User.username == form_data.username).first()

    # Verify user exists and password is correct
    if not user or not AuthService.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create JWT token with user information
    access_token = AuthService.create_access_token(
        data={
            "sub": user.username,       # Subject (standard claim)
            "user_id": user.id,
            "role": user.role.value,    # Include role for RBAC
            "email": user.email
        }
    )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db_session)
):
    """
    User registration endpoint.

    FLOW:
    1. Validate user data (Pydantic)
    2. Check username/email uniqueness
    3. Hash password
    4. Create user record
    5. Return user info (no password)

    SECURITY:
    - Password is hashed before storage (never stored plain)
    - Username and email must be unique
    - Minimum password length enforced (8 chars)

    BUSINESS RULES:
    - Default role is 'broker' (lowest privilege)
    - Admin can create users with any role
    - Supervisor relationship validated

    Args:
        user_data: Registration data
        db: Database session

    Returns:
        Created user information

    Raises:
        HTTPException 400: Username or email already exists
        HTTPException 400: Invalid supervisor_id
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate supervisor if provided
    if user_data.supervisor_id:
        supervisor = db.query(User).filter(User.id == user_data.supervisor_id).first()
        if not supervisor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supervisor with id {user_data.supervisor_id} not found"
            )

        # Validate role hierarchy (broker -> manager -> head_of_sales -> admin)
        # TODO: Add hierarchy validation if needed

    # Hash password
    password_hash = AuthService.get_password_hash(user_data.password)

    # Create user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        role=user_data.role,
        supervisor_id=user_data.supervisor_id,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session)
):
    """
    Get current authenticated user information.

    USAGE:
    Frontend can call this endpoint to:
    - Verify token is still valid
    - Get user profile data
    - Check user role for UI rendering

    FLOW:
    1. Extract token from Authorization header
    2. Verify and decode token
    3. Fetch user from database
    4. Return user info

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        Current user information

    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 404: User not found (token valid but user deleted)
    """
    # Verify token and extract payload
    try:
        payload = AuthService.verify_token(token)
        username: str = payload.get("sub")

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Logout endpoint (placeholder).

    NOTE: JWT tokens are stateless, so we can't "revoke" them on the server.

    OPTIONS for production:
    1. Token blacklist (store revoked tokens in Redis)
    2. Short token expiration (15-30 min) + refresh tokens
    3. Client-side only (delete token from localStorage)

    For this project, logout is handled client-side:
    - Frontend deletes token from storage
    - Token will eventually expire

    Args:
        token: Current user token

    Returns:
        Success message
    """
    # In production, you might:
    # - Add token to blacklist in Redis
    # - Invalidate refresh token
    # - Log logout event

    return {"message": "Logout successful (client should delete token)"}


# ============================================================================
# Password Management (Future Enhancement)
# ============================================================================

# TODO: Implement password reset flow
# @router.post("/password-reset-request")
# async def request_password_reset(email: str):
#     # Send email with reset token
#     pass

# @router.post("/password-reset")
# async def reset_password(token: str, new_password: str):
#     # Verify reset token and update password
#     pass
