# app/modules/estadisticas/service.py
from datetime import date
from typing import Literal

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.estadisticas.repository import Agrupacion, EstadisticasRepository
from app.modules.estadisticas.schema import (
    IngresosFormaPagoItem,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)


class EstadisticasService:
    def __init__(self, session: Session) -> None:
        self._repository = EstadisticasRepository(session)

    def _validar_rango_fechas(self, desde: date | None, hasta: date | None) -> None:
        if desde is not None and hasta is not None and desde > hasta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha 'desde' no puede ser mayor que la fecha 'hasta'.",
            )

    def get_resumen(self) -> ResumenResponse:
        return ResumenResponse(**self._repository.get_resumen())

    def get_ventas_periodo(
        self,
        desde: date | None = None,
        hasta: date | None = None,
        agrupacion: Agrupacion = "day",
    ) -> list[VentasPeriodoItem]:
        self._validar_rango_fechas(desde, hasta)
        rows = self._repository.get_ventas_periodo(desde, hasta, agrupacion)
        return [VentasPeriodoItem(**row) for row in rows]

    def get_productos_top(self, limit: int = 5) -> list[ProductoTopItem]:
        rows = self._repository.get_productos_top(limit)
        return [ProductoTopItem(**row) for row in rows]

    def get_pedidos_por_estado(self) -> list[PedidosEstadoItem]:
        rows = self._repository.get_pedidos_por_estado()
        return [PedidosEstadoItem(**row) for row in rows]

    def get_ingresos_por_forma_pago(
        self,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[IngresosFormaPagoItem]:
        self._validar_rango_fechas(desde, hasta)
        rows = self._repository.get_ingresos_por_forma_pago(desde, hasta)
        return [IngresosFormaPagoItem(**row) for row in rows]
