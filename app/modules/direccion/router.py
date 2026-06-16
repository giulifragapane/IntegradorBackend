from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.direccion.schema import DireccionCreate, DireccionUpdate, DireccionRead, DireccionList
from app.modules.direccion.service import DireccionService
from app.modules.usuario.schema import UsuarioRead


router = APIRouter(prefix="/api/v1/direcciones", tags=["direcciones"])


def get_direccion_service(session: Session = Depends(get_session)) -> DireccionService:
    return DireccionService(session)


@router.get("/", response_model=DireccionList, status_code=status.HTTP_200_OK)
def list_my_direcciones(
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    offset: Annotated[int, Query(ge=0, description="Cantidad de registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de registros")] = 20,
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionList:
    return svc.get_my_direcciones(usuario_id=current_user.id, offset=offset, limit=limit)


@router.post("/", response_model=DireccionRead, status_code=status.HTTP_201_CREATED)
def create_direccion(
    data: DireccionCreate,
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionRead:
    return svc.create(usuario_id=current_user.id, data=data)


@router.patch("/{direccion_id}", response_model=DireccionRead, status_code=status.HTTP_200_OK)
def update_direccion(
    direccion_id: int,
    data: DireccionUpdate,
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionRead:
    return svc.update(direccion_id=direccion_id, usuario_id=current_user.id, data=data)


@router.patch("/{direccion_id}/principal", response_model=DireccionRead, status_code=status.HTTP_200_OK)
def set_direccion_principal(
    direccion_id: int,
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> DireccionRead:
    return svc.set_principal(direccion_id=direccion_id, usuario_id=current_user.id)


@router.delete("/{direccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_direccion(
    direccion_id: int,
    current_user: Annotated[UsuarioRead, Depends(get_current_active_user)],
    svc: DireccionService = Depends(get_direccion_service),
) -> None:
    svc.soft_delete(direccion_id=direccion_id, usuario_id=current_user.id)