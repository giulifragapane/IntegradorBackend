# tests/test_estadisticas.py
"""Tests de estadísticas. EST-01/EST-02/EST-03."""
import pytest
from decimal import Decimal
from tests.conftest import _login
from app.modules.pedido.model import HistorialEstadoPedido, Pedido
 
RESUMEN  = "/api/v1/estadisticas/resumen"
VENTAS   = "/api/v1/estadisticas/ventas"
TOP      = "/api/v1/estadisticas/productos-top"
ESTADOS  = "/api/v1/estadisticas/pedidos-por-estado"
INGRESOS = "/api/v1/estadisticas/ingresos"
 
 
def _forzar_estado(db_session, pedido: Pedido, estado: str) -> None:
    prev = pedido.estado_codigo
    pedido.estado_codigo = estado
    db_session.add(HistorialEstadoPedido(
        pedido_id=pedido.id,
        estado_desde_codigo=prev,
        estado_hacia_codigo=estado,
    ))
    db_session.commit()
    db_session.refresh(pedido)
 
 
# ── Acceso ────────────────────────────────────────────────────────────────────
 
def test_resumen_sin_autenticar(client):
    assert client.get(RESUMEN).status_code == 401
 
 
def test_resumen_sin_rol_admin(client, db_session):
    from tests.conftest import _crear_usuario
    _crear_usuario(db_session, "nonadmin@test.com", "pass1234", "CLIENT")
    _login(client, "nonadmin@test.com", "pass1234")
    assert client.get(RESUMEN).status_code == 403
 
 
# ── Resumen (EST-01) ──────────────────────────────────────────────────────────
 
def test_resumen_ok(client, usuario_admin):
    """200 con los campos del schema ResumenResponse."""
    _login(client, usuario_admin.email, "pass1234")
    r = client.get(RESUMEN)
    assert r.status_code == 200
    data = r.json()
    # Campos del schema ResumenResponse
    for campo in ("ventas_hoy", "ingresos_hoy", "ingresos_mes_actual",
                  "ticket_promedio", "pedidos_activos", "pedidos_total"):
        assert campo in data, f"Falta '{campo}'"
 
 
# ── Ventas por período (EST-02) ───────────────────────────────────────────────
 
def test_ventas_ok(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.get(VENTAS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
 
 
def test_ventas_rango_invertido_400(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.get(VENTAS, params={"desde": "2025-12-31", "hasta": "2024-01-01"})
    assert r.status_code == 400
 
 
 
# ── Productos top (EST-03) ────────────────────────────────────────────────────
 
def test_productos_top_ok(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.get(TOP)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
 
 
def test_productos_top_limit(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.get(TOP, params={"limit": 3})
    assert r.status_code == 200
    assert len(r.json()) <= 3
 
 
# ── Pedidos por estado ────────────────────────────────────────────────────────
 
def test_pedidos_por_estado_ok(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.get(ESTADOS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
 
 
def test_cancelado_aparece_en_distribucion(client, db_session, usuario_admin, pedido_factory):
    """CANCELADO se incluye en el conteo por estado."""
    _login(client, usuario_admin.email, "pass1234")
    pedido = pedido_factory(usuario_id=usuario_admin.id)
    _forzar_estado(db_session, pedido, "CANCELADO")
 
    items = client.get(ESTADOS).json()
    codigos = [i["estado_codigo"] for i in items]
    assert "CANCELADO" in codigos
 
 
# ── Ingresos ──────────────────────────────────────────────────────────────────
 
def test_ingresos_ok(client, usuario_admin):
    _login(client, usuario_admin.email, "pass1234")
    r = client.get(INGRESOS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
 
 
def test_cancelado_no_suma_ingresos(client, db_session, usuario_admin, producto_factory, pedido_factory):
    """EST-01: pedido CANCELADO no impacta ingresos."""
    _login(client, usuario_admin.email, "pass1234")
 
    antes = float(client.get(RESUMEN).json()["ingresos_hoy"])
 
    prod = producto_factory(precio=Decimal("500.00"), stock=5)
    pedido = pedido_factory(usuario_id=usuario_admin.id, producto_id=prod.id)
    _forzar_estado(db_session, pedido, "CANCELADO")
 
    despues = float(client.get(RESUMEN).json()["ingresos_hoy"])
    assert despues <= antes + 0.01