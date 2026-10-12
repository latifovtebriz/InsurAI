"""Authentication and Identity endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import (
    User,
    create_access_token,
    verify_password,
)
from app.modules.platform.rbac import get_current_user_claims

router = APIRouter(prefix="/auth", tags=["Auth"])

# Static demo accounts for rapid evaluation and console preview
DEMO_USERS: dict[str, dict[str, str]] = {
    "admin": {
        "password": "admin",
        "role": "admin",
        "full_name": "System Administrator",
        "email": "admin@insurai.az",
    },
    "adjuster": {
        "password": "password",
        "role": "adjuster",
        "full_name": "Leyla Mammadova (Claims Adjuster)",
        "email": "leyla.mammadova@insurai.az",
    },
    "senior_adjuster": {
        "password": "password",
        "role": "adjuster",
        "full_name": "Farid Huseynov (Senior Claims Lead)",
        "email": "farid.huseynov@insurai.az",
    },
    "underwriter": {
        "password": "password",
        "role": "underwriter",
        "full_name": "Eldar Aliyev (Underwriter)",
        "email": "eldar.aliyev@insurai.az",
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    full_name: str
    role: str


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    role: str
    permissions: list[str]


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Authenticates a user via DB or demo credential and issues a JWT token."""
    username = req.username.strip().lower()

    # 1. Check Demo Accounts first for instant testing
    if username in DEMO_USERS:
        demo = DEMO_USERS[username]
        if req.password == demo["password"]:
            token = create_access_token(
                subject=f"demo-{username}",
                role=demo["role"],
                claims={"username": username, "full_name": demo["full_name"]},
            )
            return LoginResponse(
                access_token=token,
                user_id=f"demo-{username}",
                username=username,
                full_name=demo["full_name"],
                role=demo["role"],
            )

    # 2. Check Database User
    stmt = select(User).where(User.email == username, User.is_active.is_(True))
    user = db.scalars(stmt).first()
    if user and verify_password(req.password, user.hashed_password):
        token = create_access_token(
            subject=user.id,
            role=user.role,
            claims={"username": user.email, "full_name": user.full_name},
        )
        return LoginResponse(
            access_token=token,
            user_id=user.id,
            username=user.email,
            full_name=user.full_name,
            role=user.role,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    claims: dict[str, Any] = Depends(get_current_user_claims),
) -> UserProfileResponse:
    """Returns the current authenticated user's profile and active permissions."""
    from app.modules.platform.rbac import ROLE_PERMISSIONS_MATRIX

    role = claims.get("role", "customer")
    permissions = ROLE_PERMISSIONS_MATRIX.get(role, [])

    return UserProfileResponse(
        user_id=claims.get("sub", "unknown"),
        username=claims.get("username", claims.get("sub", "")),
        role=role,
        permissions=permissions,
    )
