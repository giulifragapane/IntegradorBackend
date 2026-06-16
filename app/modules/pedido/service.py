# app/modules/pedido/service.py
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app.core.websocket import websocket_manager
from app.modules.pedido.model import (
    DetallePedido,
    EstadoPedido,
    FormaPago,
    HistorialEstadoPedido,
    Pago,
    Pedido,
)
from app.modules.pedido.schema import PedidoCreate, PedidoEstadoUpdate, PedidoList, PedidoRead
from app.modules.pedido.unit_of_work import PedidoUnitOfWork


class PedidoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: PedidoUnitOfWork, pedido_id: int) -> Pedido:
        pedido = uow.pedidos.get_active_by_id(pedido_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        return pedido

    def _get_my_or_404(self, uow: PedidoUnitOfWork, pedido_id: int, usuario_id: int) -> Pedido:
        pedido = uow.pedidos.get_active_by_id_and_usuario(pedido_id, usuario_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        return pedido

    def _validar_forma_pago(self, uow: PedidoUnitOfWork, forma_pago_codigo: str) -> None:
        forma_pago = uow.session.get(FormaPago, forma_pago_codigo)

        if not forma_pago:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forma de pago '{forma_pago_codigo}' no encontrada.",
            )

        if not forma_pago.habilitado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Forma de pago '{forma_pago_codigo}' no habilitada.",
            )

    def _validar_estado(self, uow: PedidoUnitOfWork, estado_codigo: str) -> None:
        if not uow.session.get(EstadoPedido, estado_codigo):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Estado de pedido '{estado_codigo}' no encontrado.",
            )

    def _validar_transicion_estado(self, estado_actual: str, estado_nuevo: str) -> None:
        transiciones_validas = {
            "PENDIENTE": ["CONFIRMADO", "CANCELADO"],
            "CONFIRMADO": ["EN_PREP", "CANCELADO"],
            "EN_PREP": ["ENTREGADO", "CANCELADO"],
            "ENTREGADO": [],
            "CANCELADO": [],
        }

        if estado_nuevo not in transiciones_validas.get(estado_actual, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede cambiar el estado de {estado_actual} a {estado_nuevo}.",
            )

    def _registrar_historial(
        self,
        pedido: Pedido,
        estado_desde: str | None,
        estado_hacia: str,
        observacion: str | None = None,
    ) -> None:
        pedido.historial_estados.append(
            HistorialEstadoPedido(
                estado_desde_codigo=estado_desde,
                estado_hacia_codigo=estado_hacia,
                observacion=observacion,
            )
        )

    def _devolver_stock_del_pedido(self, uow: PedidoUnitOfWork, pedido: Pedido) -> None:
        for detalle in pedido.detalles:
            producto = uow.productos.get_by_id(detalle.producto_id)

            if producto and producto.deleted_at is None:
                producto.stock_cantidad += detalle.cantidad

                if producto.stock_cantidad > 0:
                    producto.disponible = True

                producto.updated_at = uow.now
                uow.productos.add(producto)

    async def create(self, usuario_id: int, data: PedidoCreate) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            self._validar_forma_pago(uow, data.forma_pago)

            if data.direccion_entrega_id is not None:
                direccion = uow.direcciones.get_active_by_id_and_usuario(
                    data.direccion_entrega_id,
                    usuario_id,
                )
                if not direccion:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="La dirección de entrega no existe o no pertenece al usuario.",
                    )

            pedido = Pedido(
                usuario_id=usuario_id,
                direccion_entrega_id=data.direccion_entrega_id,
                forma_pago_codigo=data.forma_pago,
                estado_codigo="PENDIENTE",
                subtotal=Decimal("0.00"),
                descuento=data.descuento,
                costo_envio=data.costo_envio,
                total=Decimal("0.00"),
                notas=data.notas,
            )

            self._registrar_historial(
                pedido=pedido,
                estado_desde=None,
                estado_hacia="PENDIENTE",
                observacion="Pedido creado.",
            )

            uow.pedidos.add(pedido)

            subtotal_pedido = Decimal("0.00")

            for item in data.detalles:
                producto = uow.productos.get_by_id(item.producto_id)

                if not producto or producto.deleted_at is not None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Producto con id={item.producto_id} no encontrado.",
                    )

                if not producto.disponible:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"El producto '{producto.nombre}' no está disponible.",
                    )

                if producto.stock_cantidad < item.cantidad:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Stock insuficiente para '{producto.nombre}'. Stock actual: {producto.stock_cantidad}.",
                    )

                precio_unitario = producto.precio_base
                subtotal_detalle = precio_unitario * item.cantidad
                subtotal_pedido += subtotal_detalle

                pedido.detalles.append(
                    DetallePedido(
                        producto_id=producto.id,
                        cantidad=item.cantidad,
                        personalizacion=item.personalizacion,
                        producto_nombre=producto.nombre,
                        precio_unitario=precio_unitario,
                        subtotal=subtotal_detalle,
                    )
                )

                producto.stock_cantidad -= item.cantidad
                if producto.stock_cantidad == 0:
                    producto.disponible = False

                producto.updated_at = uow.now
                uow.productos.add(producto)

            total = subtotal_pedido - data.descuento + data.costo_envio

            if total < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El total del pedido no puede ser negativo.",
                )

            pedido.subtotal = subtotal_pedido
            pedido.total = total
            pedido.updated_at = uow.now

            pedido.pagos.append(
                Pago(
                    forma_pago_codigo=data.forma_pago,
                    mp_status="pending",
                    mp_status_detail="pending_waiting_payment",
                    transaction_amount=total,
                    payment_method_id=data.forma_pago.lower(),
                    external_reference=str(uuid4()),
                    idempotency_key=str(uuid4()),
                )
            )

            uow.pedidos.add(pedido)

            result = PedidoRead.model_validate(pedido)

        await websocket_manager.broadcast_to_roles(
            ["ADMIN", "PEDIDOS"],
            "PEDIDO_CREATED",
            {"pedido": jsonable_encoder(result)},
        )

        return result

    def get_all_for_user(self, usuario_id: int, es_staff_pedidos: bool, offset: int = 0, limit: int = 20) -> PedidoList:
        with PedidoUnitOfWork(self._session) as uow:
            if es_staff_pedidos:
                pedidos = uow.pedidos.get_active_all(offset, limit)
                total = uow.pedidos.count_active_all()
            else:
                pedidos = uow.pedidos.get_active_by_usuario(usuario_id, offset, limit)
                total = uow.pedidos.count_active_by_usuario(usuario_id)

            return PedidoList(
                data=[PedidoRead.model_validate(pedido) for pedido in pedidos],
                total=total,
            )

    def get_by_id_for_user(self, pedido_id: int, usuario_id: int, es_staff_pedidos: bool) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id) if es_staff_pedidos else self._get_my_or_404(uow, pedido_id, usuario_id)
            return PedidoRead.model_validate(pedido)

    async def update_estado(self, pedido_id: int, data: PedidoEstadoUpdate) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            estado_anterior = pedido.estado_codigo

            self._validar_estado(uow, data.estado)
            self._validar_transicion_estado(estado_anterior, data.estado)

            if data.estado == "CANCELADO":
                self._devolver_stock_del_pedido(uow, pedido)

            pedido.estado_codigo = data.estado
            pedido.updated_at = uow.now

            self._registrar_historial(
                pedido=pedido,
                estado_desde=estado_anterior,
                estado_hacia=data.estado,
                observacion="Cambio de estado.",
            )

            uow.pedidos.add(pedido)

            result = PedidoRead.model_validate(pedido)

        await websocket_manager.broadcast_to_order(
            pedido_id,
            "PEDIDO_STATUS_UPDATED",
            {"pedido": jsonable_encoder(result)},
        )

        await websocket_manager.broadcast_to_roles(
            ["ADMIN", "PEDIDOS"],
            "PEDIDO_STATUS_UPDATED",
            {"pedido": jsonable_encoder(result)},
        )

        return result

    async def cancelar_mi_pedido(self, pedido_id: int, usuario_id: int) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_my_or_404(uow, pedido_id, usuario_id)

            if pedido.estado_codigo not in ["PENDIENTE", "CONFIRMADO"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo se pueden cancelar pedidos en estado PENDIENTE o CONFIRMADO.",
                )

            estado_anterior = pedido.estado_codigo

            self._devolver_stock_del_pedido(uow, pedido)

            pedido.estado_codigo = "CANCELADO"
            pedido.updated_at = uow.now

            self._registrar_historial(
                pedido=pedido,
                estado_desde=estado_anterior,
                estado_hacia="CANCELADO",
                observacion="Pedido cancelado por el cliente.",
            )

            uow.pedidos.add(pedido)

            result = PedidoRead.model_validate(pedido)

        await websocket_manager.broadcast_to_order(
            pedido_id,
            "PEDIDO_CANCELLED",
            {"pedido": jsonable_encoder(result)},
        )

        await websocket_manager.broadcast_to_roles(
            ["ADMIN", "PEDIDOS"],
            "PEDIDO_CANCELLED",
            {"pedido": jsonable_encoder(result)},
        )

        return result
