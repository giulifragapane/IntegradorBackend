# tests/test_pedidos.py
"""Tests de pedidos: creación, FSM de estados, historial."""

from tests.conftest import _crear_usuario, _login
 
PEDIDOS = "/api/v1/pedidos/"
 
 
def _payload(producto_id: int, cantidad: int = 1) -> dict:
    return {
        "forma_pago": "EFECTIVO",
        "detalles": [{"producto_id": producto_id, "cantidad": cantidad, "personalizacion": []}],
    }
 
 
# ── Crear pedido ──────────────────────────────────────────────────────────────
 
def test_crear_pedido_ok(client, producto_factory, db_session):
    """201 con estado PENDIENTE."""
    prod = producto_factory(stock=5)
    _crear_usuario(db_session, "c1@test.com", "pass1234", "CLIENT")
    _login(client, "c1@test.com", "pass1234")
 
    r = client.post(PEDIDOS, json=_payload(prod.id))
    assert r.status_code == 201
    assert r.json()["estado"] == "PENDIENTE"
    assert len(r.json()["detalles"]) == 1
 
 
def test_crear_pedido_sin_autenticar(client, producto_factory):
    """Sin sesión → 401."""
    prod = producto_factory(stock=5)
    r = client.post(PEDIDOS, json=_payload(prod.id))
    assert r.status_code == 401
 
 
def test_crear_pedido_sin_detalles(client, db_session):
    """Lista de detalles vacía → 422."""
    _crear_usuario(db_session, "c2@test.com", "pass1234", "CLIENT")
    _login(client, "c2@test.com", "pass1234")
    r = client.post(PEDIDOS, json={"forma_pago": "EFECTIVO", "detalles": []})
    assert r.status_code == 422
 
 
def test_crear_pedido_stock_insuficiente(client, producto_factory, db_session):
    """Cantidad > stock → 400."""
    prod = producto_factory(stock=2)
    _crear_usuario(db_session, "c3@test.com", "pass1234", "CLIENT")
    _login(client, "c3@test.com", "pass1234")
    r = client.post(PEDIDOS, json=_payload(prod.id, cantidad=10))
    assert r.status_code in (400, 409)
 
 
# ── FSM estados ───────────────────────────────────────────────────────────────
 
def test_avanzar_estado_valido(client, db_session, usuario_admin, pedido_factory):
    """PENDIENTE → CONFIRMADO → 200."""
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
 
    r = client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "CONFIRMADO"})
    assert r.status_code == 200
    assert r.json()["estado"] == "CONFIRMADO"
 
 
def test_avanzar_estado_invalido_terminal(client, db_session, usuario_admin, pedido_factory):
    """RN-01: ENTREGADO es terminal, no acepta más transiciones → 400."""
    from app.modules.pedido.model import Pedido
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
 
    # Forzar estado terminal
    p = db_session.get(Pedido, pedido.id)
    p.estado_codigo = "ENTREGADO"
    db_session.commit()
 
    r = client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "EN_PREP"})
    assert r.status_code in (400, 422)
 
 
def test_cancelado_es_terminal(client, db_session, usuario_admin, pedido_factory):
    """RN-01: CANCELADO es terminal → 400."""
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
 
    client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "CANCELADO"})
    r = client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "CONFIRMADO"})
    assert r.status_code in (400, 422)
 
 
def test_secuencia_completa(client, db_session, usuario_admin, pedido_factory):
    """PENDIENTE → CONFIRMADO → EN_PREP → ENTREGADO, todos 200."""
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
 
    for estado in ("CONFIRMADO", "EN_PREP", "ENTREGADO"):
        r = client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": estado})
        assert r.status_code == 200
        assert r.json()["estado"] == estado
 
 
def test_cambiar_estado_sin_rol(client, db_session, pedido_factory, usuario_admin):
    """CLIENT no puede cambiar estado → 403."""
    pedido = pedido_factory(usuario_id=usuario_admin.id)
    _crear_usuario(db_session, "cliente_rol@test.com", "pass1234", "CLIENT")
    _login(client, "cliente_rol@test.com", "pass1234")
 
    r = client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "CONFIRMADO"})
    assert r.status_code == 403
 
 
# ── Cancelar pedido propio ────────────────────────────────────────────────────
 
def test_cancelar_pedido_propio(client, producto_factory, db_session):
    """Cliente cancela su propio pedido → 200."""
    prod = producto_factory(stock=5)
    _crear_usuario(db_session, "c4@test.com", "pass1234", "CLIENT")
    _login(client, "c4@test.com", "pass1234")
 
    r_create = client.post(PEDIDOS, json=_payload(prod.id))
    assert r_create.status_code == 201
 
    r = client.patch(f"{PEDIDOS}{r_create.json()['id']}/cancelar")
    assert r.status_code == 200
    assert r.json()["estado"] == "CANCELADO"
 
 
# ── Historial append-only ─────────────────────────────────────────────────────
 
def test_historial_append_only(client, db_session, usuario_admin, pedido_factory):
    """Cada transición agrega entradas; las anteriores se conservan."""
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
    inicial = len(pedido.historial_estados)
 
    client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "CONFIRMADO"})
    db_session.refresh(pedido)
    assert len(pedido.historial_estados) > inicial
 
    client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "EN_PREP"})
    db_session.refresh(pedido)
    assert len(pedido.historial_estados) >= inicial + 2
 
 
def test_historial_registra_transicion(client, db_session, usuario_admin, pedido_factory):
    """El historial contiene la transición PENDIENTE → CONFIRMADO."""
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
 
    client.patch(f"{PEDIDOS}{pedido.id}/estado", json={"estado": "CONFIRMADO"})
    db_session.refresh(pedido)
 
    pares = {(h.estado_desde_codigo, h.estado_hacia_codigo) for h in pedido.historial_estados}
    assert ("PENDIENTE", "CONFIRMADO") in pares
 
 
# ── Listar ────────────────────────────────────────────────────────────────────
 
def test_listar_pedidos_sin_autenticar(client):
    assert client.get(PEDIDOS).status_code == 401
 
 
def test_listar_pedidos_ok(client, producto_factory, db_session):
    prod = producto_factory(stock=10)
    _crear_usuario(db_session, "c5@test.com", "pass1234", "CLIENT")
    _login(client, "c5@test.com", "pass1234")
 
    client.post(PEDIDOS, json=_payload(prod.id))
    r = client.get(PEDIDOS)
    assert r.status_code == 200
    assert r.json()["total"] >= 1