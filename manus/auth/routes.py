from litestar import Controller, post, get, delete
from litestar.params import Parameter
from pydantic import BaseModel
import uuid

from manus.auth import get_auth_service, get_api_key_service
from manus.db import get_database
from manus.db.models import User


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class APIKeyCreate(BaseModel):
    name: str = "Default"
    expires_in_days: int | None = None


class APIKeyResponse(BaseModel):
    key_id: str
    key_secret: str
    name: str
    created_at: str
    expires_at: str | None


class AuthController(Controller):
    path = "/auth"

    @post("/register")
    async def register(self, data: RegisterRequest) -> TokenResponse:
        db = get_database()
        with db.get_session() as session:
            existing = session.query(User).filter(User.email == data.email).first()
            if existing:
                raise ValueError("Email already registered")
            import hashlib
            user = User(
                id=f"user_{uuid.uuid4().hex[:12]}",
                username=data.username,
                email=data.email,
                password_hash=hashlib.sha256(data.password.encode()).hexdigest(),
            )
            session.add(user)
            session.commit()
        auth = get_auth_service()
        access_token = auth.create_access_token(user.id)
        refresh_token = auth.create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @post("/login")
    async def login(self, data: LoginRequest) -> TokenResponse:
        import hashlib
        db = get_database()
        with db.get_session() as session:
            user = session.query(User).filter(User.email == data.email).first()
            if not user:
                raise ValueError("Invalid credentials")
            password_hash = hashlib.sha256(data.password.encode()).hexdigest()
            if user.password_hash != password_hash:
                raise ValueError("Invalid credentials")
        auth = get_auth_service()
        access_token = auth.create_access_token(user.id)
        refresh_token = auth.create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @post("/refresh")
    async def refresh_token(self, token: str = Parameter(default=None)) -> TokenResponse:
        auth = get_auth_service()
        payload = auth.verify_token(token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")
        user_id = payload.get("sub")
        access_token = auth.create_access_token(user_id)
        refresh_token = auth.create_refresh_token(user_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )


class APIKeyController(Controller):
    path = "/api-keys"

    @post("")
    async def create_api_key(
        self,
        data: APIKeyCreate,
        user_id: str = Parameter(default=None),
    ) -> APIKeyResponse:
        if not user_id:
            raise ValueError("User ID required")
        service = get_api_key_service()
        api_key, key_secret = service.create_api_key(
            user_id=user_id,
            name=data.name,
            expires_in_days=data.expires_in_days,
        )
        return APIKeyResponse(
            key_id=api_key.id,
            key_secret=key_secret,
            name=api_key.name,
            created_at=api_key.created_at.isoformat(),
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        )

    @get("")
    async def list_api_keys(
        self,
        user_id: str = Parameter(default=None),
    ) -> list[APIKeyResponse]:
        if not user_id:
            raise ValueError("User ID required")
        service = get_api_key_service()
        keys = service.list_api_keys(user_id)
        return [
            APIKeyResponse(
                key_id=k.id,
                key_secret="",
                name=k.name,
                created_at=k.created_at.isoformat(),
                expires_at=k.expires_at.isoformat() if k.expires_at else None,
            )
            for k in keys
        ]

    @delete("/{key_id:str}", status_code=200)
    async def revoke_api_key(
        self,
        key_id: str,
    ) -> dict[str, str]:
        service = get_api_key_service()
        success = service.revoke_api_key(key_id)
        return {"success": str(success)}
