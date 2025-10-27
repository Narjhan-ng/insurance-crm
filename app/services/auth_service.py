"""
Authentication Service
JWT token creation, password hashing, and verification
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Authentication service for JWT token management and password hashing.

    WHY separate service:
    - Single responsibility: auth logic isolated
    - Reusable across endpoints
    - Testable independently
    - Easy to swap implementations (e.g., OAuth later)

    SECURITY NOTES:
    - Uses bcrypt for password hashing (industry standard)
    - JWT tokens with configurable expiration
    - HS256 algorithm for signing (symmetric)
    - Secret key from environment (never hardcode!)
    """

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.

        Args:
            plain_password: User-provided password
            hashed_password: Stored hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a plain password for storage.

        Args:
            password: Plain text password

        Returns:
            Bcrypt hashed password

        SECURITY:
        - Never store plain passwords
        - Bcrypt is slow by design (resistant to brute force)
        - Each hash is unique due to salt
        """
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload data to encode (user_id, username, role, etc.)
            expires_delta: Optional custom expiration time

        Returns:
            JWT token string

        TOKEN STRUCTURE:
        {
            "sub": "username",      # Subject (standard JWT claim)
            "user_id": 123,
            "role": "broker",
            "exp": 1234567890       # Expiration timestamp
        }

        WHY JWT:
        - Stateless authentication (no server-side sessions)
        - Scalable (any server can verify token)
        - Contains user info (no database lookup needed)
        - Industry standard
        """
        to_encode = data.copy()

        # Set expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})

        # Encode JWT with secret key
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> dict:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid, expired, or tampered

        SECURITY CHECKS:
        - Signature verification (prevents tampering)
        - Expiration check (prevents replay attacks)
        - Algorithm verification (prevents algorithm confusion)
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError as e:
            raise JWTError(f"Token validation failed: {str(e)}")

    @staticmethod
    def extract_username(token: str) -> Optional[str]:
        """
        Extract username from JWT token without full validation.

        Args:
            token: JWT token string

        Returns:
            Username if present, None otherwise

        NOTE: This does NOT verify the token!
        Use verify_token() for security-critical operations.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload.get("sub")
        except JWTError:
            return None

    @staticmethod
    def extract_user_id(token: str) -> Optional[int]:
        """
        Extract user ID from JWT token.

        Args:
            token: JWT token string

        Returns:
            User ID if present, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload.get("user_id")
        except JWTError:
            return None
