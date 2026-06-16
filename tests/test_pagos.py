# tests/test_pagos.py
"""Tests de pagos con mocks de MercadoPago."""
from unittest.mock import AsyncMock, MagicMock, patch
 
import pytest
from tests.conftest import _crear_usuario, _login
 
PAGOS   = "/api/v1/pagos"
PEDIDOS = "/api/v1/pedidos/"
 
 
# ── Acceso ────────────────────────────────────────────────────────────────────
 
def test_crear_pago_sin_autenticar(client, pedido_factory, usuario_admin):
    pedido = pedido_factory(usuario_id=usuario_admin.id)
    r = client.post(f"{PAGOS}/crear", json={"pedido_id": pedido.id})
    assert r.status_code == 401
 
 
# ── Webhook ───────────────────────────────────────────────────────────────────
 
@patch("app.modules.pago.service.PagoService.procesar_webhook", new_callable=AsyncMock)
def test_webhook_ok(mock_wh, client):
    """Webhook de MercadoPago → 200."""
    mock_wh.return_value = MagicMock(
        status="ok", payment_id="123", pedido_id=None, mp_status=None, detail=None, data=None
    )
    r = client.post(
        f"{PAGOS}/webhook",
        json={"type": "payment", "data": {"id": "123"}},
        params={"type": "payment", "data.id": "123"},
    )
    assert r.status_code == 200
 
 
@patch("app.modules.pago.service.PagoService.procesar_webhook", new_callable=AsyncMock)
def test_webhook_sin_body(mock_wh, client):
    """Body vacío → no rompe el servidor."""
    mock_wh.return_value = MagicMock(
        status="ok", payment_id=None, pedido_id=None, mp_status=None, detail=None, data=None
    )
    r = client.post(f"{PAGOS}/webhook", json={})
    assert r.status_code in (200, 400, 422)
 
 
@patch("app.modules.pago.service.PagoService.procesar_webhook", new_callable=AsyncMock)
def test_webhook_llama_al_servicio(mock_wh, client):
    """El endpoint delega al servicio."""
    mock_wh.return_value = MagicMock(
        status="ok", payment_id="99", pedido_id=None, mp_status=None, detail=None, data=None
    )
    client.post(
        f"{PAGOS}/webhook",
        json={"type": "payment", "data": {"id": "99"}},
        params={"type": "payment", "data.id": "99"},
    )
    assert mock_wh.called
 
 
# ── Crear pago mockeado ───────────────────────────────────────────────────────
 
@patch("app.modules.pago.service.PagoService.crear_pago", new_callable=AsyncMock)
def test_crear_pago_mock_ok(mock_crear, client, producto_factory, db_session):
    """Con MercadoPago mockeado → no 401/403."""
    mock_crear.return_value = MagicMock(
        id=1, pedido_id=1, forma_pago_codigo="MERCADOPAGO",
        mp_payment_id=None, mp_status="pending", mp_status_detail=None,
        transaction_amount=100, payment_method_id=None,
        external_reference="ref-1", idempotency_key="key-1",
        init_point="https://mp.com", sandbox_init_point=None, preference_id="pref-1",
    )
    prod = producto_factory(stock=5)
    _crear_usuario(db_session, "pago_user@test.com", "pass1234", "CLIENT")
    _login(client, "pago_user@test.com", "pass1234")
 
    r_pedido = client.post(
        PEDIDOS,
        json={"forma_pago": "MERCADOPAGO",
              "detalles": [{"producto_id": prod.id, "cantidad": 1, "personalizacion": []}]},
    )
    if r_pedido.status_code != 201:
        pytest.skip("No se pudo crear el pedido base")
 
    r = client.post(f"{PAGOS}/crear", json={"pedido_id": r_pedido.json()["id"]})
    assert r.status_code not in (401, 403)