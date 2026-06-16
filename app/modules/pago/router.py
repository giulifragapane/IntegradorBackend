# app/modules/pago/router.py
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.pago.schema import PagoCrearRequest, PagoResponse, WebhookResponse
from app.modules.pago.service import PagoService
from app.modules.usuario.model import Usuario

router = APIRouter(prefix="/api/v1/pagos", tags=["pagos"])


def get_pago_service(session: Session = Depends(get_session)) -> PagoService:
    return PagoService(session)


@router.post(
    "/crear",
    response_model=PagoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pago MercadoPago",
)
async def crear_pago(
    data: PagoCrearRequest,
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    svc: PagoService = Depends(get_pago_service),
) -> PagoResponse:
    return await svc.crear_pago(data, current_user)


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Webhook IPN de MercadoPago",
)
async def webhook_mercadopago(
    request: Request,
    id: Annotated[str | None, Query()] = None,
    topic: Annotated[str | None, Query()] = None,
    type: Annotated[str | None, Query()] = None,
    data_id: Annotated[str | None, Query(alias="data.id")] = None,
    svc: PagoService = Depends(get_pago_service),
) -> WebhookResponse:
    body: dict[str, Any] = {}

    try:
        body = await request.json()
    except Exception:
        body = {}

    payment_id = id or data_id

    return await svc.procesar_webhook(
        request=request,
        body=body,
        query_payment_id=payment_id,
        event_type=type,
        topic=topic,
    )



@router.get(
    "/retorno/success",
    status_code=status.HTTP_302_FOUND,
    summary="Retorno exitoso de MercadoPago",
)
def retorno_success(
    svc: PagoService = Depends(get_pago_service),
) -> RedirectResponse:
    return svc.redirect_to_store_orders("success")


@router.get(
    "/retorno/failure",
    status_code=status.HTTP_302_FOUND,
    summary="Retorno fallido de MercadoPago",
)
def retorno_failure(
    svc: PagoService = Depends(get_pago_service),
) -> RedirectResponse:
    return svc.redirect_to_store_orders("failure")


@router.get(
    "/retorno/pending",
    status_code=status.HTTP_302_FOUND,
    summary="Retorno pendiente de MercadoPago",
)
def retorno_pending(
    svc: PagoService = Depends(get_pago_service),
) -> RedirectResponse:
    return svc.redirect_to_store_orders("pending")


@router.get(
    "/{pedido_id}",
    response_model=PagoResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar pago de un pedido",
)
def get_pago_por_pedido(
    pedido_id: int,
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    svc: PagoService = Depends(get_pago_service),
) -> PagoResponse:
    return svc.get_pago_por_pedido(pedido_id, current_user)
