# app/modules/ingrediente/router.py
from fastapi import APIRouter, Depends, Query, status
from typing import Annotated
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.ingrediente.schema import IngredienteCreate, IngredienteRead, IngredienteUpdate, IngredienteList
from app.modules.ingrediente.service import IngredienteService

router = APIRouter(prefix="/ingredientes", tags=["ingredientes"])


def get_ingrediente_service(session: Session = Depends(get_session)) -> IngredienteService:
    return IngredienteService(session)


@router.post("/", response_model=IngredienteRead, status_code=status.HTTP_201_CREATED, summary="Crear un ingrediente nuevo")
def create_ingrediente(
    data: IngredienteCreate,
    _admin=Depends(require_role(["ADMIN"])),
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteRead:
    return svc.create(data)


@router.get("/", response_model=IngredienteList, status_code=status.HTTP_200_OK, summary="Listar ingredientes activos (paginado)")
def list_ingredientes(
    offset: Annotated[int, Query(ge=0, description="Cantidad de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de registros")] = 20,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteList:
    return svc.get_all_active(offset=offset, limit=limit)


@router.get("/all/", response_model=IngredienteList, status_code=status.HTTP_200_OK, summary="Listar todos los ingredientes")
def list_ingredientes_all(
    offset: Annotated[int, Query(ge=0, description="Cantidad de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de registros")] = 20,
    _admin=Depends(require_role(["ADMIN"])),
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteList:
    return svc.get_all(offset=offset, limit=limit)


@router.get("/buscar/", response_model=IngredienteRead, status_code=status.HTTP_200_OK, summary="Buscar ingrediente por nombre")
def search_ingrediente_by_nombre(
    nombre: str = Query(..., max_length=100, description="Nombre del ingrediente a buscar"),
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteRead:
    return svc.get_by_nombre(nombre)


@router.get("/alergenos/", response_model=IngredienteList, status_code=status.HTTP_200_OK, summary="Listar ingredientes alérgenos activos")
def list_alergenos(
    offset: Annotated[int, Query(ge=0, description="Cantidad de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de registros")] = 20,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteList:
    return svc.get_alergenos(offset=offset, limit=limit)


@router.get("/{ingrediente_id}", response_model=IngredienteRead, status_code=status.HTTP_200_OK, summary="Obtener ingrediente por ID")
def get_ingrediente(ingrediente_id: int, svc: IngredienteService = Depends(get_ingrediente_service)) -> IngredienteRead:
    return svc.get_by_id(ingrediente_id)


@router.patch("/{ingrediente_id}", response_model=IngredienteRead, status_code=status.HTTP_200_OK, summary="Actualización parcial de ingrediente")
def update_ingrediente(
    ingrediente_id: int,
    data: IngredienteUpdate,
    _admin=Depends(require_role(["ADMIN"])),
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteRead:
    return svc.update(ingrediente_id, data)


@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar ingrediente (soft delete)")
def delete_ingrediente(
    ingrediente_id: int,
    _admin=Depends(require_role(["ADMIN"])),
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> None:
    svc.soft_delete(ingrediente_id)