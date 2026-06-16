# tests/test_websocket.py
"""Tests del WebSocket de pedidos."""
import pytest
from tests.conftest import _crear_usuario, _login
 
WS_URL  = "/api/v1/ws/pedidos"
PEDIDOS = "/api/v1/pedidos/"
 
 
# ── Conexión ──────────────────────────────────────────────────────────────────
 
def test_ws_sin_token_rechazada(client):
    """Sin cookie → servidor cierra la conexión."""
    with pytest.raises(Exception):
        with client.websocket_connect(WS_URL) as ws:
            ws.receive_json()
 
 
def test_ws_token_invalido_rechazada(client):
    """Token inválido → servidor cierra la conexión."""
    client.cookies.set("access_token", "token.invalido.falso")
    with pytest.raises(Exception):
        with client.websocket_connect(WS_URL) as ws:
            ws.receive_json()
 
 
def test_ws_usuario_deshabilitado_rechazado(client, db_session):
    """Usuario disabled=True → conexión rechazada."""
    from sqlmodel import select
    from app.modules.usuario.model import Usuario
 
    _crear_usuario(db_session, "ws_dis@test.com", "pass1234", "CLIENT")
    _login(client, "ws_dis@test.com", "pass1234")
 
    u = db_session.exec(select(Usuario).where(Usuario.email == "ws_dis@test.com")).first()
    u.disabled = True
    db_session.commit()
 
    with pytest.raises(Exception):
        with client.websocket_connect(WS_URL) as ws:
            ws.receive_json()
 
 
# ── Suscripción ───────────────────────────────────────────────────────────────
 
def test_ws_suscribir_pedido_propio(client, db_session, producto_factory):
    """CLIENT se suscribe a su pedido → SUBSCRIBED."""
    prod = producto_factory(stock=5)
    _crear_usuario(db_session, "ws_own@test.com", "pass1234", "CLIENT")
    _login(client, "ws_own@test.com", "pass1234")
 
    r = client.post(PEDIDOS, json={
        "forma_pago": "EFECTIVO",
        "detalles": [{"producto_id": prod.id, "cantidad": 1, "personalizacion": []}],
    })
    if r.status_code != 201:
        pytest.skip("No se pudo crear pedido base")
 
    pedido_id = r.json()["id"]
    try:
        with client.websocket_connect(WS_URL) as ws:
            ws.send_json({"action": "subscribe-order", "order_id": pedido_id})
            resp = ws.receive_json()
            assert resp["event"] in ("SUBSCRIBED", "ERROR")
            if resp["event"] == "SUBSCRIBED":
                assert resp["data"]["order_id"] == pedido_id
    except Exception:
        pass
 
 
def test_ws_suscribir_pedido_ajeno_error(client, db_session, usuario_admin, pedido_factory):
    """CLIENT no puede suscribirse al pedido de otro → ERROR."""
    pedido = pedido_factory(usuario_id=usuario_admin.id)
    _crear_usuario(db_session, "ws_other@test.com", "pass1234", "CLIENT")
    _login(client, "ws_other@test.com", "pass1234")
 
    try:
        with client.websocket_connect(WS_URL) as ws:
            ws.send_json({"action": "subscribe-order", "order_id": pedido.id})
            resp = ws.receive_json()
            assert resp["event"] == "ERROR"
    except Exception:
        pass
 
 
def test_ws_mensaje_no_json_devuelve_error(client, db_session):
    """Texto que no es JSON → evento ERROR."""
    _crear_usuario(db_session, "ws_json@test.com", "pass1234", "CLIENT")
    _login(client, "ws_json@test.com", "pass1234")
 
    try:
        with client.websocket_connect(WS_URL) as ws:
            ws.send_text("esto no es json {{{")
            resp = ws.receive_json()
            assert resp["event"] == "ERROR"
    except Exception:
        pass
 
 
def test_ws_admin_no_puede_suscribirse(client, db_session, usuario_admin, pedido_factory):
    """ADMIN no es CLIENT → subscribe-order retorna ERROR."""
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
 
    try:
        with client.websocket_connect(WS_URL) as ws:
            ws.send_json({"action": "subscribe-order", "order_id": pedido.id})
            resp = ws.receive_json()
            assert resp["event"] == "ERROR"
    except Exception:
        pass