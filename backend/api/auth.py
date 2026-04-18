"""
Authentication API — User registration, login, and API key management.
"""
import logging
import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.execution import UserModel, OrganizationModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"sk_{secrets.token_urlsafe(32)}"


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    organization_name: Optional[str] = None  # Optional, creates default if not provided


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    api_key: str  # Only returned once, must be saved by client
    org_id: str
    org_name: str
    message: str


class LoginRequest(BaseModel):
    email: EmailStr


class LoginResponse(BaseModel):
    user_id: str
    email: str
    api_key: str
    org_id: str


class ApiKeyVerifyResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth Handlers
# ---------------------------------------------------------------------------


async def get_current_user(
    api_key: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """
    Dependency to get the current authenticated user from an API key.
    Usage: async def endpoint(user: UserModel = Depends(get_current_user)):
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    
    hashed = hash_api_key(api_key)
    stmt = select(UserModel).where(UserModel.hashed_api_key == hashed)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user and organization.
    
    Returns the API key ONCE — the user must save it as it cannot be recovered.
    """
    # Check if email already exists
    stmt = select(UserModel).where(UserModel.email == request.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Create organization (or use default)
    org_name = request.organization_name or f"{request.email.split('@')[0]}'s Org"
    org = OrganizationModel(name=org_name)
    db.add(org)
    await db.flush()
    
    # Generate API key
    api_key = generate_api_key()
    hashed_api_key = hash_api_key(api_key)
    
    # Create user
    user = UserModel(
        email=request.email,
        hashed_api_key=hashed_api_key,
        org_id=org.id,
        role="admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(org)
    
    logger.info(f"New user registered: {request.email}, org: {org_name}")
    
    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        api_key=api_key,  # Only returned once!
        org_id=org.id,
        org_name=org.name,
        message="Save your API key — it cannot be recovered",
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with email (for demo purposes).
    
    In production, this should verify credentials properly.
    This is a simplified version that just checks if the email exists
    and returns the API key for that user.
    
    NOTE: This endpoint is for development/testing. In production,
    implement proper password authentication.
    """
    stmt = select(UserModel).where(UserModel.email == request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # In a real system, we'd verify a password here
    # For this demo, we just return the user info
    # The API key was already returned at registration
    
    return LoginResponse(
        user_id=user.id,
        email=user.email,
        api_key="REDACTED",  # Don't expose again after registration
        org_id=user.org_id,
    )


@router.post("/verify", response_model=ApiKeyVerifyResponse)
async def verify_api_key(
    api_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify if an API key is valid.
    """
    if not api_key:
        return ApiKeyVerifyResponse(valid=False)
    
    hashed = hash_api_key(api_key)
    stmt = select(UserModel).where(UserModel.hashed_api_key == hashed)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return ApiKeyVerifyResponse(valid=False)
    
    return ApiKeyVerifyResponse(
        valid=True,
        user_id=user.id,
        org_id=user.org_id,
        role=user.role,
    )
