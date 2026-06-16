# app/modules/pago/schema.py
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PagoCrearRequest(BaseModel):
    pedido_id: int
    token: str | None = None
    payment_method_id: str | None = None
    installments: int = Field(default=1, ge=1)
    issuer_id: str | None = None


class PagoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pedido_id: int
    forma_pago_codigo: str
    mp_payment_id: int | None
    mp_status: str
    mp_status_detail: str | None
    transaction_amount: Decimal
    payment_method_id: str | None
    external_reference: str
    idempotency_key: str
    init_point: str | None = None
    sandbox_init_point: str | None = None
    preference_id: str | None = None


class WebhookResponse(BaseModel):
    status: str = "ok"
    payment_id: str | None = None
    pedido_id: int | None = None
    mp_status: str | None = None
    detail: str | None = None
    data: dict[str, Any] | None = None
