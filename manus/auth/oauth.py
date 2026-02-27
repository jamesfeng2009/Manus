from litestar import Controller, post, get
from litestar.response import Redirect
from litestar.params import Parameter
from pydantic import BaseModel
import uuid
import os
import httpx

from manus.auth import get_auth_service, get_api_key_service
from manus.db import get_database
from manus.db.models import User


class OAuthCallback(BaseModel):
    code: str
    state: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OAuthController(Controller):
    path = "/oauth"

    @get("/github")
    async def github_login(self) -> None:
        client_id = os.getenv("GITHUB_CLIENT_ID")
        redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/oauth/github/callback")
        scope = "read:user user:email"
        url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
        return Redirect(url)

    @get("/github/callback")
    async def github_callback(self, code: str = Parameter(default=None)) -> TokenResponse:
        client_id = os.getenv("GITHUB_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/oauth/github/callback")

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            github_user = user_response.json()

            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            emails = emails_response.json()
            primary_email = next((e["email"] for e in emails if e["primary"]), None)

        return await self._handle_oauth_user(
            provider="github",
            provider_id=str(github_user.get("id")),
            email=primary_email or github_user.get("email"),
            username=github_user.get("login"),
            avatar_url=github_user.get("avatar_url"),
        )

    @get("/google")
    async def google_login(self) -> None:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth/google/callback")
        scope = "openid email profile"
        url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&state=manus"
        return Redirect(url)

    @get("/google/callback")
    async def google_callback(self, code: str = Parameter(default=None)) -> TokenResponse:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth/google/callback")

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            google_user = user_response.json()

        return await self._handle_oauth_user(
            provider="google",
            provider_id=str(google_user.get("id")),
            email=google_user.get("email"),
            username=google_user.get("name") or google_user.get("email"),
            avatar_url=google_user.get("picture"),
        )

    async def _handle_oauth_user(
        self,
        provider: str,
        provider_id: str,
        email: str | None,
        username: str,
        avatar_url: str | None,
    ) -> TokenResponse:
        db = get_database()
        auth = get_auth_service()

        with db.get_session() as session:
            user = session.query(User).filter(
                User.provider == provider,
                User.provider_id == provider_id,
            ).first()

            if not user:
                if not email:
                    raise ValueError("Email not provided by OAuth provider")

                existing = session.query(User).filter(User.email == email).first()
                if existing:
                    existing.provider = provider
                    existing.provider_id = provider_id
                    existing.avatar_url = avatar_url
                    user = existing
                else:
                    user = User(
                        id=f"user_{uuid.uuid4().hex[:12]}",
                        email=email,
                        username=username,
                        provider=provider,
                        provider_id=provider_id,
                        avatar_url=avatar_url,
                        is_verified=True,
                    )
                    session.add(user)
                session.commit()

        access_token = auth.create_access_token(user.id)
        refresh_token = auth.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
