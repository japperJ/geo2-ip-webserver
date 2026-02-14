from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.models.user import User
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    TokenData,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def auth_error(status_code: int, detail: str):
    """Helper to create consistent auth error responses."""
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise auth_error(status.HTTP_409_CONFLICT, "Username already exists")
        else:
            raise auth_error(status.HTTP_409_CONFLICT, "Email already exists")
    
    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # Find user
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise auth_error(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    
    if not user.is_active:
        raise auth_error(status.HTTP_403_FORBIDDEN, "User account is disabled")
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise auth_error(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    
    user_id = payload.get("sub")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise auth_error(status.HTTP_401_UNAUTHORIZED, "Token has expired")
    
    # Create new tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: str = ""
):
    """List all users (for site admin to find users to add)."""
    query = select(User).where(User.is_admin == False)  # Don't show super admins
    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) | 
            (User.email.ilike(f"%{search}%"))
        )
    query = query.limit(50)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new user (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can create users")
    
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this email or username already exists"
        )
    
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password."""
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}
