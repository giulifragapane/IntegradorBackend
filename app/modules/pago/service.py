# app/modules/pago/service.py
import hashlib
import hmac
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app.core.config import settings
from app.core.websocket import websocket_manager
from app.modules.pago.schema import PagoCrearRequest, PagoResponse, WebhookResponse
from app.modules.pago.unit_of_work import PagoUnitOfWork
from app.modules.pedido.model import HistorialEstadoPedido, Pago, Pedido


class PagoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_sdk(self):
        if not settings.mp_access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MP_ACCESS_TOKEN no está configurado en el .env.",
            )

        try:
            import mercadopago
        except ModuleNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falta instalar MercadoPago SDK. Ejecutá: pip install mercadopago",
            ) from exc

        return mercadopago.SDK(settings.mp_access_token)

    def _usuario_tiene_rol(self, usuario, roles_permitidos: list[str]) -> bool:
        roles_usuario = getattr(usuario, "roles", []) or []
        valores_permitidos = [rol.upper() for rol in roles_permitidos]

        for rol in roles_usuario:
            rol_codigo = getattr(rol, "rol_codigo", None)
            if rol_codigo is not None and str(rol_codigo).upper() in valores_permitidos:
                return True

            codigo = getattr(rol, "codigo", None)
            if codigo is not None and str(codigo).upper() in valores_permitidos:
                return True

            if isinstance(rol, str) and rol.upper() in valores_permitidos:
                return True

        return False

    def _validar_acceso_pago(self, pedido: Pedido, usuario) -> None:
        es_staff = self._usuario_tiene_rol(usuario, ["ADMIN", "PEDIDOS"])

        if es_staff:
            return

        if pedido.usuario_id != usuario.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para acceder al pago de este pedido.",
            )

    def _pago_response(
        self,
        pago: Pago,
        init_point: str | None = None,
        sandbox_init_point: str | None = None,
        preference_id: str | None = None,
    ) -> PagoResponse:
        data = PagoResponse.model_validate(pago)
        data.init_point = init_point
        data.sandbox_init_point = sandbox_init_point
        data.preference_id = preference_id
        return data

    def _crear_o_recuperar_pago(self, uow: PagoUnitOfWork, pedido: Pedido) -> Pago:
        pago = uow.pagos.get_pago_by_pedido(int(pedido.id))

        if pago:
            return pago

        pago = Pago(
            pedido_id=int(pedido.id),
            forma_pago_codigo=pedido.forma_pago_codigo,
            mp_status="pending",
            mp_status_detail="pending_waiting_payment",
            transaction_amount=pedido.total,
            payment_method_id="mercadopago",
            external_reference=str(uuid4()),
            idempotency_key=str(uuid4()),
        )

        return uow.pagos.save(pago)

    def _request_options(self, idempotency_key: str) -> dict[str, Any]:
        return {
            "custom_headers": {
                "x-idempotency-key": idempotency_key,
            }
        }

    def _preference_payload(self, pedido: Pedido, pago: Pago) -> dict[str, Any]:
        items = [
            {
                "title": detalle.producto_nombre,
                "quantity": int(detalle.cantidad),
                "unit_price": float(detalle.precio_unitario),
                "currency_id": "ARS",
            }
            for detalle in pedido.detalles
        ]

        if not items:
            items = [
                {
                    "title": f"Pedido #{pedido.id}",
                    "quantity": 1,
                    "unit_price": float(pedido.total),
                    "currency_id": "ARS",
                }
            ]

        payload: dict[str, Any] = {
            "items": items,
            "external_reference": pago.external_reference,
            "metadata": {
                "pedido_id": int(pedido.id),
                "pago_id": int(pago.id),
            },
        }

        if settings.mp_webhook_url:
            payload["notification_url"] = settings.mp_webhook_url

        if settings.ngrok_url:
            base_return_url = settings.ngrok_url.rstrip("/")
            payload["back_urls"] = {
                "success": f"{base_return_url}/api/v1/pagos/retorno/success",
                "failure": f"{base_return_url}/api/v1/pagos/retorno/failure",
                "pending": f"{base_return_url}/api/v1/pagos/retorno/pending",
            }
            payload["auto_return"] = "approved"
        elif settings.frontend_url:
            payload["back_urls"] = {
                "success": f"{settings.frontend_url}/orders",
                "failure": f"{settings.frontend_url}/orders",
                "pending": f"{settings.frontend_url}/orders",
            }

        return payload

    def _payment_payload(
        self,
        pedido: Pedido,
        pago: Pago,
        data: PagoCrearRequest,
        email: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "transaction_amount": float(pedido.total),
            "token": data.token,
            "description": f"Pedido #{pedido.id}",
            "installments": data.installments,
            "payment_method_id": data.payment_method_id,
            "external_reference": pago.external_reference,
            "payer": {
                "email": email,
            },
            "metadata": {
                "pedido_id": int(pedido.id),
                "pago_id": int(pago.id),
            },
        }

        if data.issuer_id:
            payload["issuer_id"] = data.issuer_id

        return payload

    def _actualizar_pago_desde_mp_response(
        self,
        pago: Pago,
        response: dict[str, Any],
    ) -> None:
        if response.get("id"):
            pago.mp_payment_id = int(response["id"])

        pago.mp_status = response.get("status") or pago.mp_status
        pago.mp_status_detail = response.get("status_detail")
        pago.transaction_amount = Decimal(str(response.get("transaction_amount") or pago.transaction_amount))
        pago.payment_method_id = response.get("payment_method_id") or pago.payment_method_id

    async def crear_pago(self, data: PagoCrearRequest, usuario) -> PagoResponse:
        sdk = self._get_sdk()

        with PagoUnitOfWork(self._session) as uow:
            pedido = uow.pagos.get_pedido_active_by_id(data.pedido_id)

            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado.",
                )

            self._validar_acceso_pago(pedido, usuario)

            if pedido.forma_pago_codigo != "MERCADOPAGO":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El pedido no tiene MercadoPago como forma de pago.",
                )

            pago = self._crear_o_recuperar_pago(uow, pedido)

            if data.token:
                payment_response = sdk.payment().create(
                    self._payment_payload(pedido, pago, data, usuario.email)
                )

                mp_status_code = payment_response.get("status")
                mp_response = payment_response.get("response", {})

                if mp_status_code not in [200, 201]:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={
                            "message": "MercadoPago no pudo crear el pago.",
                            "mercadopago": mp_response,
                        },
                    )

                self._actualizar_pago_desde_mp_response(pago, mp_response)
                uow.pagos.save(pago)

                result = self._pago_response(pago)

            else:
                preference_response = sdk.preference().create(
                    self._preference_payload(pedido, pago)
                )

                mp_status_code = preference_response.get("status")
                mp_response = preference_response.get("response", {})

                if mp_status_code not in [200, 201]:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={
                            "message": "MercadoPago no pudo crear la preferencia.",
                            "mercadopago": mp_response,
                        },
                    )

                preference_id = mp_response.get("id")
                pago.mp_status = "pending"
                pago.mp_status_detail = "preference_created"
                pago.payment_method_id = "mercadopago"
                uow.pagos.save(pago)

                result = self._pago_response(
                    pago,
                    init_point=mp_response.get("init_point"),
                    sandbox_init_point=mp_response.get("sandbox_init_point"),
                    preference_id=preference_id,
                )

        return result

    def _extraer_payment_id(self, body: dict[str, Any], query_payment_id: str | None) -> str | None:
        return (
            query_payment_id
            or body.get("id")
            or body.get("data", {}).get("id")
        )

    def _evento_es_payment(self, body: dict[str, Any], event_type: str | None, topic: str | None) -> bool:
        tipo = event_type or topic or body.get("type") or body.get("topic")
        return tipo in [None, "payment"]

    def _validar_firma_webhook(
        self,
        request: Request,
        data_id: str | None,
    ) -> None:
        secret = settings.mp_webhook_secret

        if not secret:
            return

        x_signature = request.headers.get("x-signature")
        x_request_id = request.headers.get("x-request-id")

        if not x_signature or not x_request_id or not data_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firma de MercadoPago ausente o incompleta.",
            )

        signature_parts = dict(
            item.split("=", 1)
            for item in x_signature.split(",")
            if "=" in item
        )

        ts = signature_parts.get("ts")
        received_hash = signature_parts.get("v1")

        if not ts or not received_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Formato de firma MercadoPago inválido.",
            )

        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"

        calculated_hash = hmac.new(
            secret.encode(),
            manifest.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firma MercadoPago inválida.",
            )

    async def procesar_webhook(
        self,
        request: Request,
        body: dict[str, Any],
        query_payment_id: str | None,
        event_type: str | None,
        topic: str | None,
    ) -> WebhookResponse:
        payment_id = self._extraer_payment_id(body, query_payment_id)

        if not self._evento_es_payment(body, event_type, topic):
            return WebhookResponse(status="ok", detail="Evento ignorado.", data=body)

        self._validar_firma_webhook(request, payment_id)

        if not payment_id:
            return WebhookResponse(
                status="ok",
                detail="Webhook sin payment_id.",
                data=body,
            )

        sdk = self._get_sdk()
        payment_response = sdk.payment().get(payment_id)
        mp_status_code = payment_response.get("status")
        mp_response = payment_response.get("response", {})

        if mp_status_code != 200:
            return WebhookResponse(
                status="ok",
                payment_id=payment_id,
                detail="MercadoPago todavía no devolvió el pago.",
                data=mp_response,
            )

        external_reference = mp_response.get("external_reference")
        mp_payment_id = mp_response.get("id")

        pedido_id = None
        pedido_data = None
        pago_status = mp_response.get("status")

        with PagoUnitOfWork(self._session) as uow:
            pago = None

            if mp_payment_id:
                pago = uow.pagos.get_pago_by_mp_payment_id(int(mp_payment_id))

            if pago is None and external_reference:
                pago = uow.pagos.get_pago_by_external_reference(str(external_reference))

            if pago is None:
                return WebhookResponse(
                    status="ok",
                    payment_id=str(payment_id),
                    mp_status=pago_status,
                    detail="Pago no encontrado para el webhook.",
                    data=mp_response,
                )

            pedido = uow.pagos.get_pedido_active_by_id(pago.pedido_id)

            if not pedido:
                return WebhookResponse(
                    status="ok",
                    payment_id=str(payment_id),
                    mp_status=pago_status,
                    detail="Pedido no encontrado para el webhook.",
                    data=mp_response,
                )

            self._actualizar_pago_desde_mp_response(pago, mp_response)
            uow.pagos.save(pago)

            pedido_id = int(pedido.id)

            if pago.mp_status == "approved" and pedido.estado_codigo == "PENDIENTE":
                pedido.estado_codigo = "CONFIRMADO"
                pedido.updated_at = uow.now
                pedido.historial_estados.append(
                    HistorialEstadoPedido(
                        estado_desde_codigo="PENDIENTE",
                        estado_hacia_codigo="CONFIRMADO",
                        observacion="Pago aprobado por MercadoPago.",
                    )
                )
                uow.pedidos.add(pedido)

            pedido_data = {
                "id": pedido.id,
                "usuario_id": pedido.usuario_id,
                "direccion_entrega_id": pedido.direccion_entrega_id,
                "estado": pedido.estado_codigo,
                "forma_pago": pedido.forma_pago_codigo,
                "subtotal": pedido.subtotal,
                "descuento": pedido.descuento,
                "costo_envio": pedido.costo_envio,
                "total": pedido.total,
                "notas": pedido.notas,
            }

        if pedido_id and pedido_data:
            await websocket_manager.broadcast_to_order(
                pedido_id,
                "PAGO_UPDATED",
                {"pedido": jsonable_encoder(pedido_data), "pago": mp_response},
            )
            await websocket_manager.broadcast_to_roles(
                ["ADMIN", "PEDIDOS"],
                "PAGO_UPDATED",
                {"pedido": jsonable_encoder(pedido_data), "pago": mp_response},
            )

        return WebhookResponse(
            status="ok",
            payment_id=str(payment_id),
            pedido_id=pedido_id,
            mp_status=pago_status,
            data=mp_response,
        )


    def redirect_to_store_orders(self, result: str) -> RedirectResponse:
        frontend_url = settings.frontend_url.rstrip("/") if settings.frontend_url else "http://localhost:5173"
        return RedirectResponse(url=f"{frontend_url}/orders?payment={result}")

    def get_pago_por_pedido(self, pedido_id: int, usuario) -> PagoResponse:
        with PagoUnitOfWork(self._session) as uow:
            pedido = uow.pagos.get_pedido_active_by_id(pedido_id)

            if not pedido:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado.",
                )

            self._validar_acceso_pago(pedido, usuario)

            pago = uow.pagos.get_pago_by_pedido(pedido_id)

            if not pago:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pago no encontrado.",
                )

            return self._pago_response(pago)
