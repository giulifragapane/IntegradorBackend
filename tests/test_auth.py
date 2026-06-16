
# tests/test_auth.py
"""Tests de autenticación: registro, login, logout, /me, refresh_token, rate_limit."""

from tests.conftest import _login

from app.core.config import settings
 
REGISTER = "/api/v1/auth/register"
TOKEN    = "/api/v1/auth/token"
REFRESH  = "/api/v1/auth/refresh"
LOGOUT   = "/api/v1/auth/logout"
ME       = "/api/v1/auth/me"
 
# Email único por test para no contaminar el rate limiter
def _user(n: int) -> dict:
    return {"nombre": "Ana", "apellido": "Lopez", "email": f"ana{n}@test.com", "password": "pass1234"}
 
 
# ── Registro ──────────────────────────────────────────────────────────────────
 
def test_register_ok(client):
    r = client.post(REGISTER, json=_user(1))
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "ana1@test.com"
    assert "id" in data
    assert "password_hash" not in data
 
 
def test_register_email_duplicado(client):
    client.post(REGISTER, json=_user(2))
    r = client.post(REGISTER, json=_user(2))
    assert r.status_code in (400, 409, 422)
 
 
def test_register_password_corta(client):
    u = _user(3)
    u["password"] = "abc"
    r = client.post(REGISTER, json=u)
    assert r.status_code == 422
 
 
def test_register_email_invalido(client):
    u = _user(4)
    u["email"] = "no-es-email"
    r = client.post(REGISTER, json=u)
    assert r.status_code == 422
 
 
# ── Login ─────────────────────────────────────────────────────────────────────
 
def test_login_ok(client):
    u = _user(5)
    client.post(REGISTER, json=u)
    r = client.post(TOKEN, data={"username": u["email"], "password": u["password"]})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
 
 
def test_login_credenciales_invalidas(client):
    u = _user(6)
    client.post(REGISTER, json=u)
    r = client.post(TOKEN, data={"username": u["email"], "password": "wrongpassword"})
    assert r.status_code == 401
 
 
def test_login_usuario_inexistente(client):
    r = client.post(TOKEN, data={"username": "noexiste@test.com", "password": "cualquiera"})
    assert r.status_code == 401
 
 
def test_login_setea_cookie(client):
    u = _user(7)
    client.post(REGISTER, json=u)
    client.post(TOKEN, data={"username": u["email"], "password": u["password"]})
    assert "access_token" in client.cookies
 
 
# ── Logout ────────────────────────────────────────────────────────────────────
 
def test_logout_ok(client):
    u = _user(8)
    client.post(REGISTER, json=u)
    _login(client, u["email"], u["password"])
    r = client.post(LOGOUT)
    assert r.status_code == 200
 
 
# ── /me ───────────────────────────────────────────────────────────────────────
 
def test_me_autenticado(client):
    u = _user(9)
    client.post(REGISTER, json=u)
    _login(client, u["email"], u["password"])
    r = client.get(ME)
    assert r.status_code == 200
    assert r.json()["email"] == u["email"]
 
 
def test_me_sin_autenticar(client):
    assert client.get(ME).status_code == 401
 
 
# ── Refresh token ─────────────────────────────────────────────────────────────
 
def test_refresh_token_ok(client):
    """POST /refresh con cookie válida → nuevo access_token."""
    u = _user(10)
    client.post(REGISTER, json=u)
    r_login = client.post(TOKEN, data={"username": u["email"], "password": u["password"]})
    assert r_login.status_code == 200
    assert "refresh_token" in client.cookies
 
    r = client.post(REFRESH)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
 
 
def test_refresh_token_sin_cookie(client):
    """POST /refresh sin cookie → 401."""
    r = client.post(REFRESH)
    assert r.status_code == 401
 
 
# ── Rate limit (429) ──────────────────────────────────────────────────────────
 
def test_login_rate_limit_429(client):
    """Superar el límite de intentos fallidos → 429."""
    u = _user(11)
    client.post(REGISTER, json=u)
 
    max_intentos = settings.auth_rate_limit_max_attempts
    # Agotar el límite con passwords incorrectas
    for _ in range(max_intentos):
        client.post(TOKEN, data={"username": u["email"], "password": "wrong"})
 
    # El siguiente debe devolver 429
    r = client.post(TOKEN, data={"username": u["email"], "password": "wrong"})
    assert r.status_code == 429
 
 
def test_register_rate_limit_429(client):
    """Superar el límite de registros desde la misma IP → 429."""
    max_intentos = settings.auth_rate_limit_max_attempts
 
    for i in range(max_intentos):
        client.post(REGISTER, json={
            "nombre": "X", "apellido": "Y",
            "email": f"rl_reg_{i}@test.com", "password": "pass1234"
        })
 
    r = client.post(REGISTER, json={
        "nombre": "X", "apellido": "Y",
        "email": "rl_over@test.com", "password": "pass1234"
    })
    assert r.status_code == 429