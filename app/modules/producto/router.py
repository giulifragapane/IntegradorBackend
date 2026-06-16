# app/modules/producto/router.py
from fastapi import APIRouter, Depends, Query, status
from typing import Annotated
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.producto.schema import (
    ProductoCreate,
    ProductoRead,
    ProductoUpdate,
    ProductoList,
    ProductoDisponibilidadUpdate,
    UnidadMedidaList,
)
from app.modules.producto.service import ProductoService

router = APIRouter(prefix="/productos", tags=["productos"])


def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)


@router.post("/", response_model=ProductoRead, status_code=status.HTTP_201_CREATED, summary="Crear un producto nuevo")
def create_producto(
    data: ProductoCreate,
    _admin=Depends(require_role(["ADMIN"])),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoRead:
    return svc.create(data)


@router.get("/", response_model=ProductoList, status_code=status.HTTP_200_OK, summary="Listar productos activos (paginado)")
def list_productos(
    offset: Annotated[int, Query(ge=0, description="Registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de registros")] = 20,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoList:
    return svc.get_all_active(offset=offset, limit=limit)


@router.get("/all/", response_model=ProductoList, status_code=status.HTTP_200_OK, summary="Listar todos los productos")
def list_productos_all(
    offset: Annotated[int, Query(ge=0, description="Cantidad de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de registros")] = 20,
    _admin=Depends(require_role(["ADMIN", "STOCK"])),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoList:
    return svc.get_all(offset=offset, limit=limit)


@router.get("/buscar/", response_model=ProductoRead, status_code=status.HTTP_200_OK, summary="Buscar producto por nombre")
def search_producto_by_nombre(
    nombre: str = Query(..., max_length=150, description="Nombre del producto a buscar"),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoRead:
    return svc.get_by_nombre(nombre)


@router.patch("/{producto_id}/disponibilidad", response_model=ProductoRead, status_code=status.HTTP_200_OK, summary="Actualizar stock y disponibilidad de producto")
def update_producto_disponibilidad(
    producto_id: int,
    data: ProductoDisponibilidadUpdate,
    _user=Depends(require_role(["ADMIN", "STOCK"])),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoRead:
    return svc.update_disponibilidad(producto_id, data)

@router.get(
    "/unidades-medida/",
    response_model=UnidadMedidaList,
    status_code=status.HTTP_200_OK,
    summary="Listar unidades de medida",
)
def list_unidades_medida(
    offset: Annotated[int, Query(ge=0, description="Registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de registros")] = 100,
    svc: ProductoService = Depends(get_producto_service),
) -> UnidadMedidaList:
    return svc.get_unidades_medida(offset=offset, limit=limit)

@router.get("/{producto_id}", response_model=ProductoRead, status_code=status.HTTP_200_OK, summary="Obtener producto por ID")
def get_producto(producto_id: int, svc: ProductoService = Depends(get_producto_service)) -> ProductoRead:
    return svc.get_by_id(producto_id)


@router.patch("/{producto_id}", response_model=ProductoRead, status_code=status.HTTP_200_OK, summary="Actualización parcial de producto")
def update_producto(
    producto_id: int,
    data: ProductoUpdate,
    _admin=Depends(require_role(["ADMIN"])),
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoRead:
    return svc.update(producto_id, data)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar producto (soft delete)")
def delete_producto(
    producto_id: int,
    _admin=Depends(require_role(["ADMIN"])),
    svc: ProductoService = Depends(get_producto_service),
) -> None:
    svc.soft_delete(producto_id)