# app/modules/pedido/websocket_router.py
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlmodel import Session, select

from app.core.database import engine
from app.core.security import decode_access_token
from app.core.websocket import websocket_manager
from app.modules.pedido.model import Pedido
from app.modules.usuario.model import Usuario

router = APIRouter(tags=["pedidos websocket"])


def _obtener_rol_principal(usuario: Usuario) -> str:
    roles = [str(usuario_rol.rol_codigo).upper() for usuario_rol in usuario.roles]

    if "ADMIN" in roles:
        return "ADMIN"

    if "PEDIDOS" in roles:
        return "PEDIDOS"

    if "STOCK" in roles:
        return "STOCK"

    return "CLIENT"


def _pedido_pertenece_al_usuario(
    session: Session,
    pedido_id: int,
    usuario_id: int,
) -> bool:
    pedido = session.exec(
        select(Pedido)
        .where(Pedido.id == pedido_id)
        .where(Pedido.usuario_id == usuario_id)
        .where(Pedido.deleted_at.is_(None))
    ).first()

    return pedido is not None


def _pedidos_activos_del_usuario(session: Session, usuario_id: int) -> list[Pedido]:
    return list(
        session.exec(
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id)
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo.notin_(["ENTREGADO", "CANCELADO"]))
        ).all()
    )


@router.websocket("/api/v1/ws/pedidos")
async def websocket_pedidos(websocket: WebSocket) -> None:
    token = websocket.cookies.get("access_token")

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)

    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = payload.get("sub")

    if not email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    with Session(engine) as session:
        usuario = session.exec(
            select(Usuario).where(Usuario.email == email)
        ).first()

        if not usuario or usuario.deleted_at is not None or usuario.disabled:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        _ = usuario.roles
        rol = _obtener_rol_principal(usuario)
        usuario_id = int(usuario.id)

        await websocket_manager.connect(websocket, rol, usuario_id)

        if rol == "CLIENT":
            for pedido in _pedidos_activos_del_usuario(session, usuario_id):
                websocket_manager.join_order_room(websocket, int(pedido.id))

        try:
            while True:
                raw_message = await websocket.receive_text()

                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    await websocket.send_json(
                        {
                            "event": "ERROR",
                            "type": "ERROR",
                            "data": {"detail": "Mensaje WebSocket inválido."},
                        }
                    )
                    continue

                action = message.get("action")
                pedido_id = message.get("order_id") or message.get("pedido_id")

                if action == "subscribe-order":
                    if rol != "CLIENT":
                        await websocket.send_json(
                            {
                                "event": "ERROR",
                                "type": "ERROR",
                                "data": {"detail": "Solo clientes pueden suscribirse a pedidos específicos."},
                            }
                        )
                        continue

                    if not isinstance(pedido_id, int):
                        await websocket.send_json(
                            {
                                "event": "ERROR",
                                "type": "ERROR",
                                "data": {"detail": "order_id inválido."},
                            }
                        )
                        continue

                    if not _pedido_pertenece_al_usuario(session, pedido_id, usuario_id):
                        await websocket.send_json(
                            {
                                "event": "ERROR",
                                "type": "ERROR",
                                "data": {"detail": "El pedido no pertenece al usuario."},
                            }
                        )
                        continue

                    websocket_manager.join_order_room(websocket, pedido_id)
                    await websocket.send_json(
                        {
                            "event": "SUBSCRIBED",
                            "type": "SUBSCRIBED",
                            "data": {"order_id": pedido_id},
                        }
                    )

                elif action == "unsubscribe-order":
                    if isinstance(pedido_id, int):
                        websocket_manager.leave_order_room(websocket, pedido_id)
                        await websocket.send_json(
                            {
                                "event": "UNSUBSCRIBED",
                                "type": "UNSUBSCRIBED",
                                "data": {"order_id": pedido_id},
                            }
                        )

        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket)
        except Exception:
            websocket_manager.disconnect(websocket)
            raise
