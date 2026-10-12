"""Identity, authentication, and Role-Based Access Control (RBAC) engine."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from app.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_bearer = HTTPBearer(auto_error=False)

# Static Role-Permission Mapping per Architecture Section 3.12
ROLE_PERMISSIONS_MATRIX: dict[str, list[str]] = {
    "admin": ["*"],
    "underwriter": ["sales:*", "underwriting:*", "product:read", "policy:read", "traces:read", "metrics:read"],
    "adjuster": ["claims:*", "policy:read", "fraud:read", "sales:read", "underwriting:read", "traces:read", "audit:read", "metrics:read"],
    "finance_officer": ["finance:*", "claims:read", "traces:read", "metrics:read"],
    "compliance_officer": ["compliance:*", "party:read", "audit:read", "traces:read", "metrics:read"],
    "siu_investigator": ["fraud:*", "claims:read", "traces:read", "metrics:read"],
    "broker": ["sales:*", "policy:read_assigned", "underwriting:read"],
    "customer": ["policy:read_own", "claims:create", "service:read_own", "sales:create_quote"],
}


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored salt$hash string."""
    try:
        salt, key_hex = hashed_password.split("$")
        computed = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000
        )
        return secrets.compare_digest(computed.hex(), key_hex)
    except Exception:
        return False


def create_access_token(
    subject: str,
    role: str,
    claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a signed JWT access token."""
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT token."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization token"
        ) from None


def has_permission(role: str, required_permission: str) -> bool:
    """
    Checks if a role possesses the required permission.
    Supports wildcards like '*' or 'claims:*'.
    """
    allowed_list = ROLE_PERMISSIONS_MATRIX.get(role, [])
    if "*" in allowed_list:
        return True

    if required_permission in allowed_list:
        return True

    # Check wildcard module prefix
    if ":" in required_permission:
        mod_prefix = f"{required_permission.split(':')[0]}:*"
        if mod_prefix in allowed_list:
            return True

    return False


def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> dict[str, Any]:
    """Dependency that extracts validated JWT claims from Bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication header",
        )
    return decode_access_token(credentials.credentials)


def require_permission(required_permission: str):  # type: ignore
    """Factory creating FastAPI dependencies that enforce specific RBAC permissions."""

    def _permission_guard(
        claims: dict[str, Any] = Depends(get_current_user_claims),
    ) -> dict[str, Any]:
        role = claims.get("role", "")
        if not has_permission(role, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' lacks required permission '{required_permission}'",
            )
        return claims

    return _permission_guard
