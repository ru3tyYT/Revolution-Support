"""Tests for FastAPI web app and auth."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def web_env(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("SECRET_KEY", "0" * 32)
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")
    from web.config import get_web_config

    get_web_config.cache_clear()


@pytest.fixture
def client(web_env):
    from web.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_login_redirects_to_discord(client):
    with patch(
        "web.services.oauth_service.OAuthService.get_authorization_url",
        return_value="https://discord.com/api/oauth2/authorize?x=1",
    ):
        r = client.get("/api/auth/login", follow_redirects=False)
    assert r.status_code in (301, 302, 303, 307, 308)
    assert r.headers["location"].startswith("https://discord.com")


@pytest.fixture
def sample_user():
    return {
        "id": "123456789",
        "username": "testuser",
        "global_name": None,
        "avatar": None,
        "discriminator": "0",
        "guilds": [],
        "is_admin": False,
        "admin_guilds": [],
    }


def test_callback_redirects_with_token(client, sample_user):
    with patch(
        "web.services.auth_service.AuthService.authenticate_discord_user",
        new_callable=AsyncMock,
        return_value=sample_user,
    ):
        r = client.get(
            "/api/auth/callback",
            params={"code": "auth_code", "state": "state"},
            follow_redirects=False,
        )
    assert r.status_code in (301, 302, 303, 307, 308)
    loc = r.headers["location"]
    assert loc.startswith("http://localhost:5173/auth/callback?")
    assert "token=" in loc


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_valid_token(client, sample_user):
    from web.services.auth_service import AuthService

    svc = AuthService()
    token, _ = svc.create_access_token(sample_user)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["discord_id"] == sample_user["id"]
    assert data["username"] == sample_user["username"]
