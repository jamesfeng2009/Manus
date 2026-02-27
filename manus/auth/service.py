import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from manus.db import get_database
from manus.db.models import User, APIKey


class AuthService:
    def __init__(self):
        self.db = get_database()
        self.secret_key = os.getenv("JWT_SECRET_KEY", "manus-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24
        self.refresh_token_expire_days = 30

    def create_access_token(self, user_id: str, extra_claims: dict | None = None) -> str:
        from jose import jwt
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "access",
        }
        if extra_claims:
            to_encode.update(extra_claims)
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        from jose import jwt
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh",
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict[str, Any] | None:
        from jose import jwt, JWTError
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    def get_current_user(self, token: str) -> User | None:
        payload = self.verify_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        with self.db.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()


_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


class APIKeyService:
    def __init__(self):
        self.db = get_database()

    def create_api_key(
        self,
        user_id: str,
        name: str = "Default",
        expires_in_days: int | None = None,
    ) -> tuple[APIKey, str]:
        key_id = f"mk_{uuid.uuid4().hex[:8]}"
        key_secret = f"manus_sk_{uuid.uuid4().hex}"
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        with self.db.get_session() as session:
            api_key = APIKey(
                id=key_id,
                user_id=user_id,
                key_hash=self._hash_key(key_secret),
                name=name,
                expires_at=expires_at,
            )
            session.add(api_key)
            session.commit()
        return api_key, key_secret

    def verify_api_key(self, key_id: str, key_secret: str) -> User | None:
        with self.db.get_session() as session:
            api_key = session.query(APIKey).filter(APIKey.id == key_id).first()
            if not api_key:
                return None
            if api_key.key_hash != self._hash_key(key_secret):
                return None
            if api_key.is_active is False:
                return None
            if api_key.expires_at and api_key.expires_at < datetime.now():
                return None
            return session.query(User).filter(User.id == api_key.user_id).first()

    def list_api_keys(self, user_id: str) -> list[APIKey]:
        with self.db.get_session() as session:
            return session.query(APIKey).filter(APIKey.user_id == user_id).all()

    def revoke_api_key(self, key_id: str) -> bool:
        with self.db.get_session() as session:
            api_key = session.query(APIKey).filter(APIKey.id == key_id).first()
            if not api_key:
                return False
            api_key.is_active = False
            session.commit()
            return True

    def _hash_key(self, key: str) -> str:
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()


_api_key_service: APIKeyService | None = None


def get_api_key_service() -> APIKeyService:
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service
