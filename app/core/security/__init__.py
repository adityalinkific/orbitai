from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from typing import Dict, Any


class PasswordService:
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    def _hash(cls, password: str) -> str:
        return cls._pwd_context.hash(password)

    @classmethod
    def _verify(cls, password: str, hashed_password: str) -> bool:
        return cls._pwd_context.verify(password, hashed_password)


class TokenService:

    @staticmethod
    def _create_access_token(data: Dict[str, Any]) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        payload = {
            **data,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

    @staticmethod
    def _decode_access_token(token: str) -> Dict[str, Any]:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
