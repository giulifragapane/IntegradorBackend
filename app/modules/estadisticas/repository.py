# app/modules/estadisticas/repository.py
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import cast, func
from sqlalchemy.types import Date
from sqlmodel import Session, select

from app.modules.pedido.model import DetallePedido, EstadoPedido, FormaPago, Pedido

Agrupacion = Literal["day", "week", "month"]


class EstadisticasRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _inicio_dia(self, value: date) -> datetime:
        return datetime.combine(value, time.min).replace(tzinfo=timezone.utc)

    def _fin_dia(self, value: date) -> datetime:
        return datetime.combine(value, time.max).replace(tzinfo=timezone.utc)

    def _periodo_sql(self, agrupacion: Agrupacion):
        if agrupacion == "week":
            return func.date_trunc("week", Pedido.created_at)
        if agrupacion == "month":
            return func.date_trunc("month", Pedido.created_at)
        return cast(Pedido.created_at, Date)

    def _filtros_fecha(self, statement, desde: date | None, hasta: date | None):
        if desde is not None:
            statement = statement.where(Pedido.created_at >= self._inicio_dia(desde))
        if hasta is not None:
            statement = statement.where(Pedido.created_at <= self._fin_dia(hasta))
        return statement

    def get_resumen(self) -> dict:
        hoy = date.today()
        inicio_hoy = self._inicio_dia(hoy)
        fin_hoy = self._fin_dia(hoy)
        inicio_mes = datetime(hoy.year, hoy.month, 1, tzinfo=timezone.utc)

        ventas_hoy = self.session.exec(
            select(func.count(Pedido.id))
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo != "CANCELADO")
            .where(Pedido.created_at >= inicio_hoy)
            .where(Pedido.created_at <= fin_hoy)
        ).one() or 0

        ingresos_hoy = self.session.exec(
            select(func.coalesce(func.sum(Pedido.total), 0))
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo != "CANCELADO")
            .where(Pedido.created_at >= inicio_hoy)
            .where(Pedido.created_at <= fin_hoy)
        ).one() or Decimal("0.00")

        ingresos_mes_actual = self.session.exec(
            select(func.coalesce(func.sum(Pedido.total), 0))
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo != "CANCELADO")
            .where(Pedido.created_at >= inicio_mes)
        ).one() or Decimal("0.00")

        ticket_promedio = self.session.exec(
            select(func.coalesce(func.avg(Pedido.total), 0))
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo != "CANCELADO")
        ).one() or Decimal("0.00")

        pedidos_activos = self.session.exec(
            select(func.count(Pedido.id))
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo.notin_(["CANCELADO", "ENTREGADO"]))
        ).one() or 0

        pedidos_total = self.session.exec(
            select(func.count(Pedido.id))
            .where(Pedido.deleted_at.is_(None))
        ).one() or 0

        return {
            "ventas_hoy": Decimal(str(ventas_hoy)),
            "ingresos_hoy": Decimal(str(ingresos_hoy)),
            "ingresos_mes_actual": Decimal(str(ingresos_mes_actual)),
            "ticket_promedio": Decimal(str(ticket_promedio)).quantize(Decimal("0.01")),
            "pedidos_activos": int(pedidos_activos),
            "pedidos_total": int(pedidos_total),
        }

    def get_ventas_periodo(
        self,
        desde: date | None,
        hasta: date | None,
        agrupacion: Agrupacion,
    ) -> list[dict]:
        periodo = self._periodo_sql(agrupacion)

        statement = (
            select(
                periodo.label("periodo"),
                func.count(Pedido.id).label("cantidad_pedidos"),
                func.coalesce(func.sum(Pedido.total), 0).label("total_vendido"),
            )
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo != "CANCELADO")
            .group_by(periodo)
            .order_by(periodo)
        )
        statement = self._filtros_fecha(statement, desde, hasta)

        rows = self.session.exec(statement).all()
        return [
            {
                "periodo": row.periodo.isoformat() if hasattr(row.periodo, "isoformat") else str(row.periodo),
                "cantidad_pedidos": int(row.cantidad_pedidos),
                "total_vendido": Decimal(str(row.total_vendido)),
            }
            for row in rows
        ]

    def get_productos_top(self, limit: int) -> list[dict]:
        statement = (
            select(
                DetallePedido.producto_id.label("producto_id"),
                DetallePedido.producto_nombre.label("producto_nombre"),
                func.coalesce(func.sum(DetallePedido.cantidad), 0).label("cantidad_vendida"),
                func.coalesce(func.sum(DetallePedido.subtotal), 0).label("ingresos_total"),
            )
            .join(Pedido, Pedido.id == DetallePedido.pedido_id)
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo != "CANCELADO")
            .group_by(DetallePedido.producto_id, DetallePedido.producto_nombre)
            .order_by(func.sum(DetallePedido.cantidad).desc())
            .limit(limit)
        )

        rows = self.session.exec(statement).all()
        return [
            {
                "producto_id": int(row.producto_id),
                "producto_nombre": row.producto_nombre,
                "cantidad_vendida": int(row.cantidad_vendida),
                "ingresos_total": Decimal(str(row.ingresos_total)),
            }
            for row in rows
        ]

    def get_pedidos_por_estado(self) -> list[dict]:
        statement = (
            select(
                Pedido.estado_codigo.label("estado_codigo"),
                EstadoPedido.nombre.label("estado_nombre"),
                func.count(Pedido.id).label("cantidad"),
            )
            .join(EstadoPedido, EstadoPedido.codigo == Pedido.estado_codigo)
            .where(Pedido.deleted_at.is_(None))
            .group_by(Pedido.estado_codigo, EstadoPedido.nombre, EstadoPedido.orden)
            .order_by(EstadoPedido.orden)
        )

        rows = self.session.exec(statement).all()
        return [
            {
                "estado_codigo": row.estado_codigo,
                "estado_nombre": row.estado_nombre,
                "cantidad": int(row.cantidad),
            }
            for row in rows
        ]

    def get_ingresos_por_forma_pago(
        self,
        desde: date | None,
        hasta: date | None,
    ) -> list[dict]:
        statement = (
            select(
                Pedido.forma_pago_codigo.label("forma_pago_codigo"),
                FormaPago.nombre.label("forma_pago_nombre"),
                func.coalesce(func.sum(Pedido.total), 0).label("ingresos_total"),
                func.count(Pedido.id).label("cantidad_pedidos"),
            )
            .join(FormaPago, FormaPago.codigo == Pedido.forma_pago_codigo)
            .where(Pedido.deleted_at.is_(None))
            .where(Pedido.estado_codigo != "CANCELADO")
            .group_by(Pedido.forma_pago_codigo, FormaPago.nombre)
            .order_by(func.sum(Pedido.total).desc())
        )
        statement = self._filtros_fecha(statement, desde, hasta)

        rows = self.session.exec(statement).all()
        return [
            {
                "forma_pago_codigo": row.forma_pago_codigo,
                "forma_pago_nombre": row.forma_pago_nombre,
                "ingresos_total": Decimal(str(row.ingresos_total)),
                "cantidad_pedidos": int(row.cantidad_pedidos),
            }
            for row in rows
        ]
