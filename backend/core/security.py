"""
Security utilities for authentication, password hashing, and API key management.
Migrated from app/core/security.py — only config import changed.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import hmac
import secrets
import structlog

from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from django.conf import settings

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        logger.warning("jwt_token_expired")
        return None
    except JWTError:
        logger.warning("jwt_token_invalid")
        return None


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    salted_key = f"{api_key}{settings.API_KEY_HASH_SALT}"
    return hashlib.sha256(salted_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    return hmac.compare_digest(hash_api_key(api_key), hashed_key)


def get_api_key_prefix(api_key: str, length: int = 8) -> str:
    return api_key[:length]
