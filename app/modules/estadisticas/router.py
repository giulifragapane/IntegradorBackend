# app/modules/estadisticas/router.py
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.estadisticas.repository import Agrupacion
from app.modules.estadisticas.schema import (
    IngresosFormaPagoItem,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)
from app.modules.estadisticas.service import EstadisticasService
from app.modules.usuario.schema import UsuarioRead

router = APIRouter(prefix="/api/v1/estadisticas", tags=["estadisticas"])


def get_estadisticas_service(session: Session = Depends(get_session)) -> EstadisticasService:
    return EstadisticasService(session)


AdminUser = Annotated[UsuarioRead, Depends(require_role(["ADMIN"]))]


@router.get(
    "/resumen",
    response_model=ResumenResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener resumen de KPIs para el dashboard",
)
def get_resumen(
    _admin: AdminUser,
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> ResumenResponse:
    return svc.get_resumen()


@router.get(
    "/ventas",
    response_model=list[VentasPeriodoItem],
    status_code=status.HTTP_200_OK,
    summary="Obtener ventas agrupadas por período",
)
def get_ventas_periodo(
    _admin: AdminUser,
    desde: Annotated[date | None, Query(description="Fecha inicial YYYY-MM-DD")] = None,
    hasta: Annotated[date | None, Query(description="Fecha final YYYY-MM-DD")] = None,
    agrupacion: Annotated[Agrupacion, Query(description="day, week o month")] = "day",
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> list[VentasPeriodoItem]:
    return svc.get_ventas_periodo(desde=desde, hasta=hasta, agrupacion=agrupacion)


@router.get(
    "/productos-top",
    response_model=list[ProductoTopItem],
    status_code=status.HTTP_200_OK,
    summary="Obtener productos más vendidos",
)
def get_productos_top(
    _admin: AdminUser,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> list[ProductoTopItem]:
    return svc.get_productos_top(limit=limit)


@router.get(
    "/pedidos-por-estado",
    response_model=list[PedidosEstadoItem],
    status_code=status.HTTP_200_OK,
    summary="Obtener distribución de pedidos por estado",
)
def get_pedidos_por_estado(
    _admin: AdminUser,
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> list[PedidosEstadoItem]:
    return svc.get_pedidos_por_estado()


@router.get(
    "/ingresos",
    response_model=list[IngresosFormaPagoItem],
    status_code=status.HTTP_200_OK,
    summary="Obtener ingresos agrupados por forma de pago",
)
def get_ingresos_por_forma_pago(
    _admin: AdminUser,
    desde: Annotated[date | None, Query(description="Fecha inicial YYYY-MM-DD")] = None,
    hasta: Annotated[date | None, Query(description="Fecha final YYYY-MM-DD")] = None,
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> list[IngresosFormaPagoItem]:
    return svc.get_ingresos_por_forma_pago(desde=desde, hasta=hasta)
